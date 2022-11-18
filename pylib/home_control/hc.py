#!/usr/bin/python3
'''home-control: smart device and scene controller

---------- usage

Command-line usage:
  hc [--flags] target [command]

Library usage:
  hc.control(target: str, command: str='on', settings: dict={}) -> List[str]

"target" is the name of a device or scene to send a command to.
The default command is "on" if not specified.

---------- user notes

The data* files construct two dictionaries: DEVICES and SCENES

DEVICES maps device names (or name patterns) to a plugin name and
plugin-specific params to actuate the command.  For example, if you have a
TpLink brand smart-switch with a fixed IP address and want to forward whatever
command was received (%c, e.g. "on" or "off"), you might have the entry.
  'bedroom': 'TPLINK:192.168.11.12:%c'

(The TPLINK plugin takes 2 params, the first is the hostname-or-IP to send the
command to, and the second is the command to send.)

If you're able to arrange for all your TpLink devices to have DNS hostnames
that begin with "tp-", then a single entry could cover all your TpLink devices:
  'tp-*': 'TPLINK:%d:%c'        # %d for device-name, i.e. the LHS of the dict.

Note that to get fixed-and-known IP addresses or DNS names for TpLink devices,
you probably need a customized DHCP server and/or DNS server.

Various plugins are supported, for example, if you can arm your home alarm
system via an HTTP web request.  The WEB plugin takes 1 param: the URL to GET.
  'arm-alarm': 'WEB:alarmcontroller/arm?mode=%c'

(You may need to create a customzed plugin if your alarm controlled requires
advanced authentication.  Use plugin-web.py as a starting point.)

The left-side (device names) can also include a command-specification, to
cover cases where different actions are needed for different commands:
  'stereo:on':  'WEB:stereocontroller/activate',
  'stereo:off': 'WEB:stereocontroller/deactivate'

A with-command match will be sought first, then falls-back to a
device-name-only match.

-----

SCENES maps from a scene name to a list of things to do when that scene is
activated.  Those things can be either: {device:command} or {scene:command}.

If a :command is not provided (for either a device or scene), then "%c" is
implied, i.e. the scene will pass-down whatever command it was given.

An example to take several actions when you leave the house:
  'away': [ 'all-lights:off', 'arm-alarm:on' ]
  'all-lights': [ 'bedroom', 'living_room', ... ]

In that example, the command given to 'away' doesn't matter, because it
overrides the commands for all its right-side elements.  However, 'all-lights'
could be passed either 'on' or 'off' to control all the listed lights.

-----

The DELAY plugin allows more advanced arrangements, for example to turn off
all the lights except the bedroom:
  SCENES = { 'just-bedroom': [ 'all-lights:off', 'delay-then:2:bedroom:on' ] }
  DEVICES = { 'delay-then': 'DELAY:%1:%2:%3',
              'bedroom': 'TPLINK:tp-bedroom:%c' }

or to turn on the bedroom light for a 2 minutes:
  SCENES = { 'bedroom_2min': [ 'bedroom:on', 'delay-then:120:bedroom:off' ] }

or to get real fancy, turn on the bedroom lights for the number of seconds
specified in the command param:
  SCENES = { 'bedroom_for': [ 'bedroom:on', 'delay-then:%c:bedroom:off' ] }

You would activate this via:  ./hc bedroom_for 120

-----

Plugin API:
init(settings: dict[str, str]) -> list[str]

Called once, upon plug-in load.  give the primary settings dict, which the
plugin may extract already set settings from, or may alter or add additional
settings, if it needs to.  Returns a list of supported plug-in name strings.

control(plugin_name: string, plugin_params: dict[str, str],
        device_name: string, command: string) ->  Tuple[bool, str]

This method actually asks the plug-in to accept and act on a command.
By way of example, if hc.control('device1', 'on') was called, and the devices
data file contained:   { 'device1': 'plugin1:params1' }, then the plugin's
control method would be called as:
  pluginmodule.control(plugin_name='plugin1', plugin_params='param1',
                       device_name='device1', command='on')

Returns a bool indicating success and a human readable string with details.
If the plugin isn't synchronous (e.g. queues actions for later, or operates
in send-and-forget mode), then "success" just means that the command was
successfully queued.
'''

import argparse, fnmatch, glob, os, pprint, site, sys, time
from dataclasses import dataclass
from typing import Any
import kcore.uncommon as UC
import kcore.varz as V


# ---------- global state

# These are initialized lazilly in control() so expensive initialization only
# occurs once (on 1st call) when used as a library.

DEVICES =  None   # dict from device name to device-action-name and plugin params
PLUGINS =  None   # dict from device-action-names to plugin module instances
SCENES =   None   # dict from scene name to action list
SETTINGS = {}     # dict from setting name to value

# ---------- settings abstraction

# INITIAL_SETTINGS drives the available flags for the command-line interface,
# and the .name and .default values provide the default settings that will be
# used for either CLI or API if no caller settings are provided.

@dataclass
class Setting:
  name: str
  default: Any
  help: str = None
  short_flag: str = None

INITIAL_SETTINGS = [
  Setting('data_dir',    ['.'],          'base directories in which to search for data files (see also private_dir)'),
  Setting('datafiles',   ['hcdata*.py'], 'glob-list of files (within data_dir) to load devices and scenes from', '-D'),
  Setting('debug',       False,          'print debugging info', '-d'),
  Setting('fast',        False,          'use send-and-forget mode.  quicker run, always assumes success (retries disabled)', '-f'),
  Setting('nosub',       False,          'do not auto-search for substring matches against device and scene names', '-n'),
  Setting('plugin_args', [],             'plugin-specific settings in the form key=value', '-p'),
  Setting('plugins_dir', ['.'],          'base directories in which to search for plugin files (see also private_dir)'),
  Setting('plugins',     ['plugin_*.py'],'glob-list of files to load as plugins'),
  Setting('private_dir' ,'private.d',    'extra directory (relative to data_dir and plugins_dir) in which to search for files.  Note: if you change this, you might need to make corresponding changes to .gitignore to keep your files private.', '-P'),
  Setting('retry',       0,              "Try this many times upon network error contacting target", '-r'),
  Setting('retry_delay', 5,              "Seconds to wait between retry attampts"),
  Setting('quiet',       False,          "Show no output if everything worked out in the end (i.e. after any retries)", '-q'),
  Setting('test',        False,          "Just show what would be done, don't do it.", '-T'),
  Setting('timeout',     5,              'default timeout for external communications', '-t'),
]


# ---------- data initialization

def init_settings(baseline_settings):
  global SETTINGS
  if SETTINGS is baseline_settings: return

  SETTINGS = baseline_settings or SETTINGS or {}  # use our caller's instance so they can see modifications made later.  e.g. this is used by test_hc to get SETTINGS['TEST_VALS'], which is added by plugin_test.init()

  # Copy over anything needed from default settings
  for s in INITIAL_SETTINGS:
    if s.name not in SETTINGS:
      SETTINGS[s.name] = s.default
    else:
      if isinstance(s.default, int): SETTINGS[s.name] = int(SETTINGS[s.name])

  # In-case any plugins (e.g. plugin_delay) need to make recursive calls back into this module:
  SETTINGS['_control'] = control

  # Shared list of threads, in-case we need to wait for them before CLI exit.
  SETTINGS['_threads'] = []


def reset():
  '''Clear out any previous data loads.  Generally only needed for unit testing.'''
  global DEVICES, PLUGINS, SCENES, SETTINGS
  DEVICES = PLUGINS = SCENES =  SETTINGS = None


def file_finder2(list_of_dirs, privdir, list_of_globs):
  found = []
  for d0 in list_of_dirs:
    if not d0: continue
    for d in [d0, os.path.join(d0, privdir)]:
      for g in list_of_globs:
        f = glob.glob(os.path.join(d, g))
        if SETTINGS['debug']: print(f'DEBUG: searching {d} for {g}, found: {f}')
        found.extend(f)
  return found


def file_finder(primary_base_dirs, privdir, list_of_globs):
  try1 = file_finder2(primary_base_dirs, privdir, list_of_globs)
  if try1: return try1
  srch2 = [os.environ.get('HC_DATA_DIR'),
           os.path.dirname(__file__),
           os.path.join(site.getusersitepackages(), 'home_control')]
  return file_finder2(srch2, privdir, list_of_globs)


def load_plugins(settings):
  '''returns dict of plugin prefix strings to plugin module instances.'''
  plugin_files = file_finder(settings['plugins_dir'], settings['private_dir'], settings['plugins'])
  if SETTINGS['debug']: print(f'DEBUG: plugin_files={plugin_files}')
  plugins = {}
  for i in plugin_files:
    new_module = UC.load_file_as_module(i)
    pi_names = new_module.init(settings)
    for j in pi_names:
      if j not in plugins:
        plugins[j] = new_module
        if SETTINGS['debug']: print(f'DEBUG: plugin {j} -> {i}')
      else:
        if SETTINGS['debug']: print(f'DEBUG: skipping {i}; already have {j}')
  if not plugins: print('WARNING- no plugins found.', file=sys.stderr)
  V.set('plugins-loaded', len(plugins))
  return plugins


def load_data(settings):
  datafiles = file_finder(settings['data_dir'], settings['private_dir'], settings['datafiles'])
  scenes = {}
  devices = {}
  for f in datafiles:
    temp_module = UC.load_file_as_module(f)
    devices, scenes = temp_module.init(devices, scenes)
  if not devices: print('WARNING- no device data found.', file=sys.stderr)
  if not scenes: print('WARNING- no scene data found.', file=sys.stderr)
  V.set('devices-loaded', len(devices))
  V.set('scenes-loaded', len(scenes))
  return devices, scenes


# ---------- primary logic

def find_target(search_dict, target, command):
  if not target: return None

  # Try a command-specific match.
  dev_command = f'{target}:{command}'
  if dev_command in search_dict: return dev_command

  # Try a direct name match
  if target in search_dict: return target

  # Finally, try for a substring match
  if SETTINGS['nosub']: return None
  matches = []
  for k, v in search_dict.items():
    if ':' in k: continue  # ignore command-specific overrides when searching for substrings; will basicaly always create a useless dup of the non-overidden target.
    if target in k: matches.append(k)

  if len(matches) == 1:
    if SETTINGS['debug']: print(f'DEBUG: successful substring match {target} -> {matches[0]}')
    return matches[0]

  elif len(matches) > 1 and (SETTINGS.get('cli') or SETTINGS['debug']):
    print(f'Multiple substring matches for {target}; ignoring.  {matches}')

  return None  # Couldn't find a matching target.


def run_scene_expansion(scene_action_list, command):
  q = UC.ParallelQueue(single_threaded=SETTINGS['debug'])
  for i in scene_action_list:
    if ':' in i:
      target_i, command_i = i.split(':', 1)
    else:
      target_i = i
      command_i = command
    q.add(control, target_i, command_i, SETTINGS, False)

  overall_okay = True
  outputs = []
  queue_out = q.join(timeout=int(SETTINGS['timeout']))
  for i, i_out in enumerate(queue_out):
    if i_out and len(i_out) == 2:
      ok, answer = i_out
    else:
      ok, answer = False, f'{scene_action_list[i]} -> timeout'
    if SETTINGS['debug']: print(f'DEBUG: {scene_action_list[i]} -> ok={ok}, answer={answer}')
    if not ok: overall_okay = False
    outputs.append(answer)

  return overall_okay, outputs


def send_device_command(target, command, device_action):
  plugin_name, plugin_params = device_action.split(':', 1)
  plugin_module = PLUGINS.get(plugin_name)
  if not plugin_module: return False, f'plugin {plugin_name} not found'
  if SETTINGS['test']:
    return True, f'TEST mode: would send {target}->{command} to plugin {plugin_name}(plugin_params={plugin_params})'
  ok, answer = plugin_module.control(plugin_name, plugin_params, target, command)

  # --- Retry logic.
  if not ok and SETTINGS['retry'] > 0:
    retries = 0
    while retries < SETTINGS['retry']:
      retries += 1
      msg = f'DEBUG: initial attempt failed; retry #{retries} of {SETTINGS["retry"]} after {SETTINGS["retry_delay"]} seconds; {answer}'
      if SETTINGS['debug'] or (SETTINGS.get('cli') and not SETTINGS['quiet']): print(msg)
      V.bump('retries')
      time.sleep(SETTINGS['retry_delay'])
      ok, answer = plugin_module.control(plugin_name, plugin_params, target, command)
    answer += f'  [{retries} retries]'

  return ok, answer


# ---------- primary API entry

def control(target, command='on', settings=None, top_level_call=True):
  '''Initiate sending a command to a target device or scene.

  "target" is a string name of a scene or device registered in the scene or
  device data files.  "command" is a string of a command accepted by whatever
  plug-in eventually handles the request.  "settings" is a dict[str, str], see
  INITIAL_SETTINGS for available options.  "top_level_call" should always
  be left True for external callers.  It's set to False internally when
  scenes make recursive calls to control(), and allows for skipping expensive
  initialization that would have occurred during the top level call.

  Return value is Tuple[bool, str | List[str | List...]].  The bool is a
  single value reflecting overall success.  If some plugins are operating
  asynchronously, this might just indicate command(s) were successfully queued
  or sent, not that they ended up successful.  If the original top-level
  target was a simple device, the 2nd part of the tuple will be a simple
  string with human-readable results of the operation.  If the original target
  was a scene, you get back a list of result strings for each action the scene
  expanded to.  Scenes can have arbitrary levels of recursion, so some of the
  lists items may be additional nested lists.  The "human readable" results
  are generated by whichever plugins are called.  In the event of a scene,
  multiple different plugins may be used for different devices, so the strings
  might not look similar to each other.
  '''
  # ----- initialize our global state, if needed.
  if top_level_call:
    init_settings(settings)   # popualtes global SETTINGS
    global DEVICES, PLUGINS, SCENES, SETTINGS
    if not PLUGINS: PLUGINS = load_plugins(SETTINGS)
    if not DEVICES: DEVICES, SCENES = load_data(SETTINGS)
    if SETTINGS['debug']:
      print(f'DEBUG: loaded {len(PLUGINS)} plugins, {len(DEVICES)} devices, and {len(SCENES)} scenes.')
      print(f'DEBUG: SETTINGS={SETTINGS}')
    V.bump('cmd-count-%s' % command)

  # ----- Check if this is a scene, and if so run its expansion.
  new_target = find_target(SCENES, target, command)
  if new_target:
    target = new_target
    scene_action_list = SCENES[target]
    if SETTINGS['debug']: print(f'DEBUG: scene {target}:{command} -> {scene_action_list}')
    overall_okay, outputs = run_scene_expansion(scene_action_list, command)
    if top_level_call: V.bump('scenes-success' if overall_okay else 'scenes-not-full-success')
    return overall_okay, outputs

  # ----- Check if this is a simple device action, and take it if so.
  new_device = find_target(DEVICES, target, command)
  if new_device:
    target = new_device
    device_action = DEVICES[target]
    if SETTINGS['debug']: print(f'DEBUG: control device {target} -> {command}')
    ok, answer = send_device_command(target, command, device_action)
    V.bump('device-success' if ok else 'device-fail')
    return ok, answer

  # ----- :-(
  V.bump('unknown target')
  return False, f'Dont know what to do with target {target}'


# ---------- command-line main

def parse_args(argv):
  ap = argparse.ArgumentParser(description='home controller')
  for s in INITIAL_SETTINGS:
    args = [f'--{s.name}']
    if s.short_flag: args.append(f'{s.short_flag}')
    kwargs = { 'default': s.default,  'help': s.help }
    if s.default is False: kwargs['action'] = 'store_true'
    if isinstance(s.default, list): kwargs['nargs'] = '*'
    ap.add_argument(*args, **kwargs)
  # add fixed positional arguments.
  ap.add_argument('target', help='device or scene to command')
  ap.add_argument('command', nargs='?', default='on', help='command to send to target')
  return ap.parse_args()


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  # Translate args to arg_settings
  arg_settings = {}
  for key, value in vars(args).items(): arg_settings[key] = value
  arg_settings['cli'] = True

  # and pass to the library API (side effect: arg_settings -> global SETTINGS)
  rslt = control(args.target, args.command, arg_settings)

  # Pretty print the results.
  if not rslt[0] or not SETTINGS['quiet']:
    try:
      # If run w/o a term, this raises "Inappropriate ioctl for device".
      width = os.get_terminal_size().columns
    except OSError:
      width = 80
    pprint.pprint(rslt, indent=2, width=width, compact=True,
                  stream=sys.stdout if rslt[0] else sys.stderr)

  # if there are any lingering threads, finish them up before exiting.
  if SETTINGS['_threads']: print('waiting for pending threads to finish...')
  for i in SETTINGS['_threads']: i.join()

  return 0 if rslt[0] else 1


if __name__ == '__main__':
  sys.exit(main())
