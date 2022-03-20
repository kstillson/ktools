
import socket
from struct import pack


SETTINGS = None

def init(settings):
  global SETTINGS
  SETTINGS = settings
  return ['TPLINK', 'tp-link', 'tplink', 'tp']   # All equivalent


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
  # generic bulb targets
  'bulb-on'      : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":1}}}',
  'bulb-off'     : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":0}}}',
  'bulb-on-slow' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":10000,"on_off":1}}}',
  'bulb-off-slow': '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":10000,"on_off":0}}}',
  'bulb-dim:@@'  : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":1,"brightness":@@}}}',
  'bulb-dim'     : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":1,"brightness":4}}}',
  'bulb-med'     : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"on_off":1,"brightness":40}}}',
  'bulb-full'    : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":1000,"on_off":1,"brightness":100}}}',
  'bulb-reboot'  : '{"smartlife.iot.common.system":{"reboot":{"delay":1}}}',
  'bulb-reset'   : '{"smartlife.iot.common.system":{"reset":{"delay":1}}}',

  # variable white temperature bulb targets
  'bright-white': '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":9000,"brightness":100}}}',
  'white'       : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":9000,"brightness":50}}}',
  'med-white'   : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":9000,"brightness":50}}}',
  'dim-white'   : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":5000,"brightness":5}}}',
  'bright-warm' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":3000,"brightness":100}}}',
  'med-warm'    : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":3000,"brightness":50}}}',
  'dim-warm'    : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"color_temp":3000,"brightness":4}}}',

  # multi-color bulb targets
  'red' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":0,"saturation":100,"brightness":75,"color_temp":0}}}',
  'dim-red' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":300,"saturation":100,"brightness":15,"color_temp":0}}}',
  'green' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":120,"saturation":100,"brightness":75,"color_temp":0}}}',
  'blue' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":240,"saturation":100,"brightness":75,"color_temp":0}}}',
  'yellow' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":60,"saturation":100,"brightness":75,"color_temp":0}}}',
  'orange' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":30,"saturation":100,"brightness":75,"color_temp":0}}}',
  'pink' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":300,"saturation":100,"brightness":75,"color_temp":0}}}',
  'purple' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":300,"saturation":100,"brightness":50,"color_temp":0}}}',
  'purple2' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":285,"saturation":100,"brightness":75,"color_temp":0}}}',
  ##
  'color:@@' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":@@,"saturation":100,"brightness":75,"color_temp":0}}}',
  'color-dim:@@' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":2000,"mode":"normal","on_off":1,"hue":@@,"saturation":100,"brightness":15,"color_temp":0}}}',
  'color-slow:@@' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":20000,"mode":"normal","on_off":1,"hue":@@,"saturation":100,"brightness":75,"color_temp":0}}}',
  'color-dim-slow:@@' : '{"smartlife.iot.smartbulb.lightingservice":{"transition_light_state":{"ignore_default":1,"transition_period":20000,"mode":"normal","on_off":1,"hue":@@,"saturation":100,"brightness":15,"color_temp":0}}}',
}


def control(plugin_name, plugin_params, device_name, dev_command):
  hostname, command = plugin_params.split(':', 1)
  hostname = hostname.replace('%d', device_name)
  command = command.replace('%c', dev_command)

  if ':' in command:
    tmp, cmd_param = command.split(':', 1)
    command = tmp + ':@@'
  else:
    cmd_param = None

  tplink_cmd = CMD_LOOKUP.get(command)
  if not tplink_cmd: return f'{device_name}: unknown tplink command: {command}'

  if cmd_param: tplink_cmd = tplink_cmd.replace('@@', cmd_param)
  if SETTINGS['debug']: print('sending %s : %s' % (device_name, tplink_cmd))

  sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    sock_tcp.settimeout(SETTINGS['timeout'])
    sock_tcp.connect((device_name, 9999))
    sock_tcp.send(encrypt(tplink_cmd))
  except Exception as e:
    return f'{device_name}: error: {str(e)}'
  if not SETTINGS['debug']:   # async mode; send and forget
    sock_tcp.close()
    return f'{device_name}: sent'
  resp = sock_tcp.recv(2048)
  sock_tcp.close()
  out = decrypt(resp[4:])
  return f'{device_name}: {out}'

