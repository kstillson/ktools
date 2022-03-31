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

'''

import argparse, fnmatch, glob, os, site, sys
from dataclasses import dataclass
from typing import Any


# ---------- global state

# These are initialized lazilly in control() so expensive initialization only
# occurs once (on 1st call) when used as a library.

DEVICES = None    # dict from device name to device-action-name and plugin params
PLUGINS = None    # dict from device-action-names to plugin module instances
SCENES =  None    # dict from scene name to action list
SETTINGS = None   # dict from setting name to value

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
  Setting('data-dir',    ['.'],          'base directories in which to search for data files (see also private-dir)'),
  Setting('datafiles',   ['hcdata*.py'], 'glob-list of files (within data-dir) to load devices and scenes from', '-D'),
  Setting('debug',       False,          'print debugging info and use syncronous mode (no parallelism)', '-d'),
  Setting('plugin-args', [],             'plugin-specific settings in the form key=value', '-p'),
  Setting('plugins-dir', ['.'],          'base directories in which to search for plugin files (see also private-dir)'),
  Setting('plugins',     ['plugin_*.py'],'glob-list of files to load as plugins'),
  Setting('private-dir' ,'private.d',    'extra directory (relative to data-dir and plugins-dir) in which to search for files.  Note: if you change this, you might need to make corresponding changes to .gitignore to keep your files private.', '-P'),
  Setting('test',        False,          "Just show what would be done, don't do it.", '-T'),
  Setting('timeout',     5,              'default timeout for external communications', '-t'),
]

# ---------- general support

def _load_file_as_module(filename, desired_module_name=None):
  if not desired_module_name: desired_module_name = filename.replace('.py', '')
  import importlib.machinery, importlib.util
  loader = importlib.machinery.SourceFileLoader(desired_module_name, filename)
  spec = importlib.util.spec_from_loader(desired_module_name, loader)
  new_module = importlib.util.module_from_spec(spec)
  loader.exec_module(new_module)
  return new_module


# ---------- data initialization

def init_settings(baseline_settings):
  global SETTINGS

  SETTINGS = baseline_settings or SETTINGS or {}  # use our caller's instance so they can see modifications made later.  e.g. this is used by test_hc to get SETTINGS['TEST_VALS'], which is added by plugin_test.init()

  # Copy over anything needed from default settings
  for s in INITIAL_SETTINGS:
    if s.name not in SETTINGS: SETTINGS[s.name] = s.default

  # In-case any plugins (e.g. plugin_delay) need to make recursive calls back into this module:
  SETTINGS['_control'] = control

  # Shared list of threads, in-case we need to wait for them before CLI exit.
  SETTINGS['_threads'] = []


def reset():
  '''Clear out any previous data loads.  Generally only needed for unit testing.'''
  global DEVICES, PLUGINS, SCENES, SETTINGS
  DEVICES = PLUGINS = SCENES =  SETTINGS = None


def file_finder(list_of_base_dirs, privdir, list_of_globs):
  found = []
  for d0 in list_of_base_dirs:
    if not d0: continue
    for d in [d0, os.path.join(d0, privdir)]:
      for g in list_of_globs:
        f = glob.glob(os.path.join(d, g))
        if SETTINGS['debug']: print(f'DEBUG: searching {d} for {g}, found: {f}')
        found.extend(f)
  return found


def load_plugins(settings):
  '''returns dict of plugin prefix strings to plugin module instances.'''
  plugin_files = file_finder(
    settings['plugins-dir'] + [os.path.dirname(__file__), os.path.join(site.getusersitepackages(), 'home_control')],
    settings['private-dir'], settings['plugins'])
  if SETTINGS['debug']: print(f'DEBUG: {plugin_files=}')
  plugins = {}
  for i in plugin_files:
    new_module = _load_file_as_module(i)
    pi_names = new_module.init(settings)
    for j in pi_names:
      plugins[j] = new_module
      if SETTINGS['debug']: print(f'DEBUG: plugin {j} -> {i}')
  if not plugins: print('WARNING- no plugins found.', file=sys.stderr)
  return plugins


def load_data(settings):
  datafiles = file_finder(settings['data-dir'] + [os.environ.get('HC_DATA_DIR')],
                          settings['private-dir'], settings['datafiles'])
  scenes = {}
  devices = {}
  for f in datafiles:
    temp_module = _load_file_as_module(f)
    devices, scenes = temp_module.init(devices, scenes)
  if not devices: print('WARNING- no device data found.', file=sys.stderr)
  if not scenes: print('WARNING- no scene data found.', file=sys.stderr)
  return devices, scenes


# ---------- primary logic

WILDCARD_DEVICES = None

def find_device_action(target, command):
  # Lazy init of list of wildcard-based matches
  global WILDCARD_DEVICES
  if WILDCARD_DEVICES is None:
    WILDCARD_DEVICES = []
    for dev in DEVICES:
      if '*' in dev: WILDCARD_DEVICES.append(dev)

  # Try a command-specific match.
  dev_command = f'{target}:{command}'
  if dev_command in DEVICES: return DEVICES[dev_command]

  # Try a direct device name match
  if target in DEVICES: return DEVICES[target]

  # Try for wildcard command-specific match
  for candidate in WILDCARD_DEVICES:
    if ':' not in candidate: continue
    if fnmatch.fnmatch(dev_command, candidate): return DEVICES[candidate]

  # And finally try for a wildcard direct match
  for candidate in WILDCARD_DEVICES:
    if fnmatch.fnmatch(target, candidate): return DEVICES[candidate]

  return None  # Couldn't find a matching device.


# ---------- primary API entry

def control(target, command='on', settings=None):

   # ----- initialize our global state, if needed.
  global DEVICES, PLUGINS, SCENES, SETTINGS
  init_settings(settings)   # popualtes global SETTINGS
  if not PLUGINS: PLUGINS = load_plugins(SETTINGS)
  if not DEVICES: DEVICES, SCENES = load_data(SETTINGS)
  if SETTINGS['debug']:
    print(f'DEBUG: loaded {len(PLUGINS)} plugins, {len(DEVICES)} devices, and {len(SCENES)} scenes.')
    print(f'DEBUG: {SETTINGS=}')

  # ----- control logic
  if SETTINGS['debug']: print(f'DEBUG: control request {target} -> {command}')

  # Check if this is a simple device action, and take it if so.
  device_action = find_device_action(target, command)
  if device_action:
    plugin_name, plugin_params = device_action.split(':', 1)
    plugin_module = PLUGINS.get(plugin_name)
    if not plugin_module: return f'plugin {plugin_name} not found'
    if SETTINGS['test']:
      return f'TEST mode: would send {target}->{command} to plugin {plugin_name}({plugin_params})'
    else:
      return plugin_module.control(plugin_name, plugin_params, target, command)

  # Check if this is a scene, and if so run its expansion.
  scene_list = SCENES.get(target)
  if not scene_list: return f'Dont know what to do with target {target}'

  outputs = []
  for i in scene_list:
    if ':' in i:
      target_i, command_i = i.split(':', 1)
    else:
      target_i = i
      command_i = command
    answer = control(target_i, command_i)
    if SETTINGS['debug']: print(f'DEBUG: {target} -> {command} returned {answer}')
    outputs.append(answer)
  return outputs


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

  # Translate args to settings
  settings = {}
  for key, value in vars(args).items(): settings[key] = value

  # and pass to the library API
  print(control(args.target, args.command, settings))

  # if there are any lingering threads, finish them up before exiting.
  if SETTINGS['_threads']: print('waiting for pending threads to finish...')
  for i in SETTINGS['_threads']: i.join()
  return 0


if __name__ == '__main__':
  sys.exit(main())
