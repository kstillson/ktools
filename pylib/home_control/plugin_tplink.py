#!/usr/bin/python3

'''Send commands to TP-Link smart switches, bulbs, plugs, etc.

This is primarily a TP-Link plug-in for the home-control system, but can also
be used as a direct executable if scenes, device management and command
normalization aren't needed.

Command normalization is an attempt to deal with the fact that different
TP-Link devices need different commands to do functionally the same thing.
For example, switches and non-dimmable plugs both accept the 'on' command, but
smart-bulbs require 'bulb-on'.  If calling this module directly, you're going
to have to figure all that out for yourself and only send appropriate commands
to devices.  In a "hc" scene, you're sending the same command to multiple
devices, so if they use different commands internally, some translation is
necessary.  For "hc", this is driven by the plugin-name parameter.  Commands
will be automatically translated to the appropriate subset for smart-bulbs
(when plugin-name is "TPLINK-BULB"), smart-plugs ("TPLINK-PLUG") and dimmable
switches ("TPLINK").  Commands that support normalization, and which are
therefore safe to use in scenes that mix devices of different types, are:

  on, off, dim, med, full, and dim:@@
  bulb-on, bulb-on-slow, bulb-off, bulb-off-slow,
  bulb-dim, bulb-med, bulb-full, and bulb-dim:@@

So, for example, if the comamnd dim:40 is recevied when
plugin_name='TPLINK-BULB', it will be run as-is, but if
plugin_name='TPLINK-PLUG', then it will be translated to 'on' (for any dimming
percentage above 0%).

'''

import argparse, socket, sys
from struct import pack

DEFAULT_TIMEOUT = 5
SETTINGS = {}


# ---------- TpLink protocol

# "Encryption" and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171
# Derived from tplink-smartplug
# git clone https://github.com/softScheck/tplink-smartplug.git

def encrypt(string):
  key = 171
  result = pack('>I', len(string))
  for i in string:
    a = key ^ ord(i)
    key = a
    result += bytes([a])
  return result


def decrypt(string):
  key = 171
  result = ""
  for i in string:
    ##py2: a = key ^ ord(i)
    a = key ^ i
    ##py2: key = ord(i)
    key = i
    result += chr(a)
  return result


CMD_LOOKUP = {
 #
 # ========== NORMALIZABLE COMMANDS (i.e. safe to send commands of any type to
 #            any device, so long as plugin_name is assigned correctly.)

 # ---------- on/off plug targets also supported by dimmer wall switches (hs220)
  'on'       : '{"system":{"set_relay_state":{"state":1}}}',
  'off'      : '{"system":{"set_relay_state":{"state":0}}}',

 # ---------- dimmer wall switches (e.g. hs220)
  'dim:@@'   : [ '{"system":{"set_relay_state":{"state":1}}}',
                 '{"smartlife.iot.dimmer":{"set_brightness":{"brightness":@@}}}' ],
  'dim'      : [ '{"system":{"set_relay_state":{"state":1}}}',
                 '{"smartlife.iot.dimmer":{"set_brightness":{"brightness":20}}}' ],
  'med'      : [ '{"system":{"set_relay_state":{"state":1}}}',
                 '{"smartlife.iot.dimmer":{"set_brightness":{"brightness":60}}}' ],
  'full'     : [ '{"system":{"set_relay_state":{"state":1}}}',
                 '{"smartlife.iot.dimmer":{"set_brightness":{"brightness":100}}}' ],

 # ---------- bulbs
  'bulb-on'      : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":1}}}',
  'bulb-off'     : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":0}}}',
  'bulb-on-slow' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":10000,"on_off":1}}}',
  'bulb-off-slow': '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":10000,"on_off":0}}}',
  'bulb-dim:@@'  : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":1,"brightness":@@}}}',
  'bulb-dim'     : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":1,"brightness":4}}}',
  'bulb-med'     : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":1,"brightness":40}}}',
  'bulb-full'    : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":1000,"on_off":1,"brightness":100}}}',

 #
 # ========== NON-NORMALIZABLE COMMANDS (only send these to the correc device types)
 #

 # ---------- in common to most tplink targets
  'info'     : '{"system":{"get_sysinfo":{}}}',
  'cloudinfo': '{"cnCloud":{"get_info":{}}}',
  'wlanscan' : '{"netif":{"get_scaninfo":{"refresh":0}}}',
  'time'     : '{"time":{"get_time":{}}}',
  'schedule' : '{"schedule":{"get_rules":{}}}',
  'countdown': '{"count_down":{"get_rules":{}}}',
  'antitheft': '{"anti_theft":{"get_rules":{}}}',
  'reboot'   : '{"system":{"reboot":{"delay":1}}}',
  'reset'    : '{"system":{"reset":{"delay":1}}}',
  'energy'   : '{"emeter":{"get_realtime":{}}}',   # Only supported on some units.

 # ---------- bulbs
  'bulb-reboot'  : '{"smartlife.iot.common.system":{"reboot":{"delay":1}}}',
  'bulb-reset'   : '{"smartlife.iot.common.system":{"reset":{"delay":1}}}',

  # variable white temperature bulb targets
  'bulb-bright-white': '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":9000,"brightness":100}}}',
  'bulb-white'       : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":9000,"brightness":50}}}',
  'bulb-med-white'   : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":9000,"brightness":50}}}',
  'bulb-dim-white'   : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":5000,"brightness":5}}}',
  'bulb-bright-warm' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":3000,"brightness":100}}}',
  'bulb-med-warm'    : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":3000,"brightness":50}}}',
  'bulb-dim-warm'    : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":3000,"brightness":4}}}',

  # multi-color bulb targets
  'bulb-red' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":0,"saturation":100,"brightness":75,"color_temp":0}}}',
  'bulb-dim-red' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":300,"saturation":100,"brightness":15,"color_temp":0}}}',
  'bulb-green' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":120,"saturation":100,"brightness":75,"color_temp":0}}}',
  'bulb-blue' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":240,"saturation":100,"brightness":75,"color_temp":0}}}',
  'bulb-yellow' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":60,"saturation":100,"brightness":75,"color_temp":0}}}',
  'bulb-orange' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":30,"saturation":100,"brightness":75,"color_temp":0}}}',
  'bulb-pink' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":300,"saturation":100,"brightness":75,"color_temp":0}}}',
  'bulb-purple' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":300,"saturation":100,"brightness":50,"color_temp":0}}}',
  'bulb-purple2' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":285,"saturation":100,"brightness":75,"color_temp":0}}}',
  ##
  'bulb-color:@@' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":@@,"saturation":100,"brightness":75,"color_temp":0}}}',
  'bulb-color-dim:@@' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":@@,"saturation":100,"brightness":15,"color_temp":0}}}',
  'bulb-color-slow:@@' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":20000,"mode":"normal","on_off":1,"hue":@@,"saturation":100,"brightness":75,"color_temp":0}}}',
  'bulb-color-dim-slow:@@' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":20000,"mode":"normal","on_off":1,"hue":@@,"saturation":100,"brightness":15,"color_temp":0}}}',
}


def normalize(plugin_type, hostname_in, command_in):
  command = command_in
  # Remove any hostname hints
  hostname = hostname_in.replace('BULB-tp-', 'tp-')
  hostname = hostname.replace('PLUG-tp-', 'tp-')

  # And map commands according to plugin-type
  if plugin_type in ['TPLINK', 'switch']:
    command = command.replace('bulb-', '').replace('-slow', '').replace('dim:0', 'off')

  elif plugin_type in ['TPLINK-PLUG', 'plug']:
    command = command.replace('bulb-', '').replace('-slow', '').replace('dim:0', 'off')
    if command.startswith('dim'): command = 'on'
    if command in ['med', 'full']: command = 'on'

  elif plugin_type in ['TPLINK-BULB', 'bulb']:
    if not command.startswith('bulb-'): command = 'bulb-' + command

  else:
    print(f'ERROR- unknown plugin name: {plugin_type}; command normalization skipped', file=sys.stderr)

  if SETTINGS['debug']:
    if hostname != hostname_in: print(f'DEBUG: hostname "{hostname_in}" normalized to "{hostname}"')
    if command != command_in: print(f'DEBUG: command "{command_in}" normalized to "{command}"')
  return hostname, command


# ---------- hc plugin API entry points


def init(settings):
  global SETTINGS
  SETTINGS = settings
  return ['TPLINK', 'TPLINK-BULB', 'TPLINK-PLUG']


def control(plugin_name, plugin_params, device_name, dev_command):
  plugin_params = plugin_params.replace('%d', device_name).replace('%c', dev_command)
  hostname, command = plugin_params.split(':', 1)
  hostname, command = normalize(plugin_name, hostname, command)
  return tplink_send(hostname, command)


# ---------- actually send a tplink device command

def tplink_send(hostname, command):
  if ':' in command:
    tmp, cmd_param = command.split(':', 1)
    command = tmp + ':@@'  # (This is what to we'll earch for in CMD_LOOKUP)
  else:
    cmd_param = None

  raw_cmds = CMD_LOOKUP.get(command)
  if not raw_cmds: return False, f'{hostname}: unknown tplink command: {command}'

  if not isinstance(raw_cmds, list):
    return tplink_send_raw(hostname, raw_cmds, cmd_param)

  all_ok = True
  answers = []
  for i in raw_cmds:
    ok, resp = tplink_send_raw(hostname, i, cmd_param)
    if not ok: all_ok = False
    answers.append(resp)
  return all_ok, ','.join(answers)  # device level commands are supposed to return strings, not lists, so much the answers together.


def tplink_send_raw(hostname, raw_cmd, cmd_param):
  if cmd_param: raw_cmd = raw_cmd.replace('@@', cmd_param)

  if SETTINGS['test']: return True, f'would send {hostname} : {raw_cmd}'
  if SETTINGS['debug']: print(f'DEBUG: sending {hostname} : {raw_cmd}')

  sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    sock_tcp.settimeout(int(SETTINGS.get('timeout', DEFAULT_TIMEOUT)))
    sock_tcp.connect((hostname, 9999))
    sock_tcp.send(encrypt(raw_cmd))
  except Exception as e:
    return False, f'{hostname}: error: {str(e)}'
  if SETTINGS['quick']:   # async mode; send and forget
    sock_tcp.close()
    return True, f'{hostname}: sent'
  resp = sock_tcp.recv(2048)
  sock_tcp.close()
  out = decrypt(resp[4:])
  ok = '"err_code":0' in out
  if SETTINGS.get('raw', False) is False and ok: out = 'ok'
  return ok, f'{hostname}: {out}'


# ---------- command line main

def main():
  global SETTINGS
  ap = argparse.ArgumentParser(description='tplink command sender')
  ap.add_argument('--debug', '-d', action='store_true', help='wait for response, print extra diagnostics')
  ap.add_argument('--normalize', '-n', default=None, help='normalize the command for specified device type (switch,plug,bulb)')
  ap.add_argument('--raw', '-r', action='store_true', help='return raw output rather than simplified')
  ap.add_argument('--test', '-T', action='store_true', help='print what would be done without doing it')
  ap.add_argument('--timeout', '-t', default=DEFAULT_TIMEOUT, help='timeout for response (seconds)')
  ap.add_argument('hostname', help='device to control (dns or ip)')
  ap.add_argument('command', nargs='?', default='on', help='command to send')
  args = ap.parse_args()
  SETTINGS['debug'] = args.debug
  SETTINGS['test'] = args.test
  SETTINGS['raw'] = args.raw
  SETTINGS['timeout'] = args.timeout
  if args.normalize:
    args.hostname, args.command = normalize(args.normalize, args.hostname, args.command)
  return tplink_send(args.hostname, args.command)


if __name__ == '__main__':
  print(main())
