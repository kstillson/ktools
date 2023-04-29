#!/usr/bin/python3

'''Send commands to TP-Link smart switches, bulbs, plugs, etc.

This is primarily a TP-Link plug-in for the home-control system, but can also
be used as a direct executable if scenes, device management and command
normalization aren't needed.

In a "hc" scene, you're sending the same command to multiple devices, so if
they use different commands internally, some translation is necessary.  For
"hc", this is driven by the plugin-name parameter.  Commands will be
automatically translated ("normalized") to the appropriate subset for
smart-bulbs (when plugin-name is "TPLINK-BULB"), smart-plugs ("TPLINK-PLUG")
and dimmable switches ("TPLINK-SWITCH").  Commands that support normalization,
and which are therefore safe to use in scenes that mix devices of different
types, are:

  on, off, dim, med, full, and dim:@@
  bulb-on, bulb-on-slow, bulb-off, bulb-off-slow,
  bulb-dim, bulb-med, bulb-full, and bulb-dim:@@

So, for example, if the comamnd dim:40 is recevied when
plugin_name='TPLINK-BULB', it will be run as-is, but if
plugin_name='TPLINK-PLUG', then it will be translated to 'on' (for any dimming
percentage above 0%).

'''

import argparse, socket, sys
from struct import pack, unpack

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

# ---------- in common to most tplink targets

  'info'       : '{"system":{"get_sysinfo":{}}}',
  'level'      : '{"system":{"get_sysinfo":{}}}',  # same query as info, but will return current dimming level
  'bulb-info'  : '{"system":{"get_sysinfo":{}}}',
  'bulb-level' : '{"system":{"get_sysinfo":{}}}',  # same query as info, but will return current dimming level

 #
 # ========== NON-NORMALIZABLE COMMANDS (only send these to the correc device types)
 #

 # ---------- in common to most tplink targets
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


def normalize_command(plugin_type, command_in):
  command = command_in

  # And map commands according to plugin-type
  if plugin_type == 'TPLINK-SWITCH':
    command = command.replace('bulb-', '').replace('-slow', '').replace('dim:0', 'off')

  elif plugin_type == 'TPLINK-PLUG':
    command = command.replace('bulb-', '').replace('-slow', '').replace('dim:0', 'off')
    if command.startswith('dim'): command = 'on'
    if command in ['med', 'full']: command = 'on'

  elif plugin_type == 'TPLINK-BULB':
    if not command.startswith('bulb-'): command = 'bulb-' + command

  else:
    print(f'ERROR- unknown plugin name: {plugin_type}; command normalization skipped', file=sys.stderr)

  if SETTINGS['debug']:
    if command != command_in: print(f'DEBUG: command "{command_in}" normalized to "{command}"')
  return command


# ---------- hc plugin API entry points


def init(settings):
  global SETTINGS
  SETTINGS = settings
  return ['TPLINK-SWITCH', 'TPLINK-BULB', 'TPLINK-PLUG']


def control(plugin_name, plugin_params, device_name, dev_command):
  plugin_params = plugin_params.replace('%d', device_name).replace('%c', dev_command)
  hostname, command = plugin_params.split(':', 1)
  command = normalize_command(plugin_name, command)
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

  if command in ['info', 'level', 'bulb-info', 'bulb-level']:
    ok, out = tplink_send_raw(hostname, raw_cmds, cmd_param, return_raw=True, fast_mode=False)
    if command in ['level', 'bulb-level']: out = f'{hostname}: {parse_json_level(command, out)}'
    return ok, out

  if not isinstance(raw_cmds, list):
    ok, out = tplink_send_raw(hostname, raw_cmds, cmd_param)
    return ok, out

  # We have a list of commands to run, do them in sequence...
  all_ok = True
  answers = []
  for i in raw_cmds:
    ok, resp = tplink_send_raw(hostname, i, cmd_param)
    if not ok: all_ok = False
    answers.append(resp)
  return all_ok, ','.join(answers)  # device level commands are supposed to return strings (not lists), so moosh the answers together.


def parse_json_level(command, raw_output):
    import json
    try:
      _, json_from_device = raw_output.split(': ', 1)  # format is "hostname: json"
      data = json.loads(json_from_device)
      si = data['system']['get_sysinfo']
      if command.startswith('bulb-'):
        relay = si['light_state']['on_off']
        if relay in [0, '0']: return 'off'
        return si.get('brightness', 'on') ##@@
      else:
        relay = si['relay_state']
        if relay in [0, '0']: return 'off'
        return si.get('brightness', 'on')
    except Exception as e:
      return f'?: {str(e)}: {raw_output}'


def tplink_send_raw(hostname, raw_cmd, cmd_param=None, return_raw='auto', fast_mode='auto'):
  if cmd_param: raw_cmd = raw_cmd.replace('@@', cmd_param)
  if return_raw == 'auto': return_raw = SETTINGS.get('raw', False)
  if fast_mode == 'auto': fast_mode = SETTINGS.get('fast', False)

  if SETTINGS['test']: return True, f'would send {hostname} : {raw_cmd}'
  if SETTINGS['debug']: print(f'DEBUG: sending {hostname} : {raw_cmd}')

  sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    sock_tcp.settimeout(int(SETTINGS.get('timeout', DEFAULT_TIMEOUT)))
    sock_tcp.connect((hostname, 9999))
    sock_tcp.send(encrypt(raw_cmd))
  except Exception as e:
    return False, f'{hostname}: error exception: {str(e)}'
  if fast_mode:   # async mode; send and forget
    sock_tcp.close()
    return True, f'{hostname}: sent'

  packed_length = sock_tcp.recv(4)
  length = unpack('>I', packed_length)[0]
  if SETTINGS['debug']: print(f'DEBUG: header indcates expected length of {length}')

  resp = b''
  chunk_len = 256
  while len(resp) < length:
    chunk = sock_tcp.recv(chunk_len, socket.MSG_WAITALL)
    resp += chunk
    if SETTINGS['debug']: print(f'DEBUG: received chunk of len {len(chunk)}')
    if not chunk or not return_raw: break

  sock_tcp.close()
  out = decrypt(resp)

  if SETTINGS['debug']: print(f'DEBUG: command to {hostname} returned: {out}')
  ok = '"err_code":0' in out
  if not return_raw: out = 'ok' if ok else 'error'
  return ok, f'{hostname}: {out}'


# ---------- command line main

def main():
  ap = argparse.ArgumentParser(description='tplink command sender')
  ap.add_argument('--debug', '-d', action='store_true', help='wait for response, print extra diagnostics')
  ap.add_argument('--json', '-j', action='store_true', help='send command as raw json (see https://github.com/softScheck/tplink-smartplug/blob/master/tplink-smarthome-commands.txt)')
  ap.add_argument('--normalize', '-n', default=None, help='normalize the command for specified device type (switch,plug,bulb)')
  ap.add_argument('--raw', '-r', action='store_true', help='return raw output rather than simplified')
  ap.add_argument('--test', '-T', action='store_true', help='print what would be done without doing it')
  ap.add_argument('--timeout', '-t', default=DEFAULT_TIMEOUT, help='timeout for response (seconds)')
  ap.add_argument('hostname', help='device to control (dns or ip)')
  ap.add_argument('command', nargs='?', default='on', help='command to send')
  args = ap.parse_args()

  # Copy appropriate items from args to SETTINGS
  global SETTINGS
  for i in ['debug', 'raw', 'test', 'timeout']: SETTINGS[i] = getattr(args, i)

  if args.normalize:
    plugin_type = f'TPLINK-{args.normalize.upper()}'
    args.command = normalize_command(plugin_type, args.command)

  if args.json:
    return tplink_send_raw(args.hostname, args.command)

  return tplink_send(args.hostname, args.command)


if __name__ == '__main__':
  print(main())
