#!/usr/bin/python3

'''Deprecated tplink controller; although still used by tools-etc/party-lights.py

This is the predecessor to ../home_control.  It doesn't have a plug-in system and
all the data is hard-coded into the source-code..  But it does support passing
through some lower-level commands with less fuss.

Specifically, ./party_lights.py uses some of the "color:..." commands, and for
the moment, I'm being lazy and providing this old interface for party_lights to
continue to call, rather than re-implementing the ability to send these lower
level commands in home_control.  So that's why this old thing is still around.

NOTE- the find_hostname() function contains an assumption that all Tp-Link
device hostnames begin with the prefix "tp-".  If that's not how your DNS
system works, you'll want to remove that assumption.

'''

# $1 is a key from SCENE_LOOKUP or hostname
# $2 is a command from CMD_LOOKUP (unneeded/unused for a scene)
# call from command-line, or public API is control(...)

# Derived from tplink-smartplug
# git clone https://github.com/softScheck/tplink-smartplug.git

import argparse, requests, socket, sys, syslog, time
from struct import pack

class Args(object): pass
ARGS = Args()  # Needs to exist even if main() isn't called (this can be a library)
ARGS.debug = False
ARGS.timeout = 8


SCENE_LOOKUP = {
 # Area-based
  'bedrm_off'   : [ 'bedrm:off' ],
  'bedrm_dim'   : [ 'bedrm:dim:20' ],
  'bedrm_med'   : [ 'bedrm:dim:40' ],
  'bedrm_full'  : [ 'bedrm:full' ],
  'down_dim'    : [ 'main:dim', 'kit:dim' ],
  'down_med'    : [ 'main:med', 'kit:med' ],
  'inside_full' : [ 'inside:full' ],
  'inside_med'  : [ 'inside:med' ],
  'inside_off'  : [ 'inside:off' ],
  'outside_full': [ 'lantern:b-full', 'door-entry:b-full', 'patio:on', 'rear-flood:on', 'out-all:on' ],
  'outside_off' : [ 'lantern:b-off', 'door-entry:b-off', 'patio:off', 'rear-flood:off', 'out-all:off' ],

 # Area based aliases
  'outside:full': [ 'outside_full', 'out-all:on' ],
  'outside:off' : [ 'outside_off', 'out-all:off' ],
  'outside_on'  : [ 'outside_full', 'out-all:on' ],

 # Activity-based
  'away'        : [ 'main:off', '$office:dim:40' ],
  'bedtime'     : [ 'inside:off', '$bedroom-light:dim:10' ],
  'comp'        : [ 'fam:off', 'kit:off', 'office:dim:55', 'lounge:off', 'bendy:off', 'window-lights:off' ],
  'cooking'     : [ 'kitchen:dim:60', 'kitchen-pendants:dim:60', 'breakfast-nook:off' ],
  'dining'      : [ 'main:off', '$family-room-left:dim:50', '$family-room-right:dim:20', '$dining-chandelier:25' ],
  'home'        : [ 'office:med', 'lounge:dim:30', 'kitchen:dim:60', 'dining-chandelier:dim:30' ],
  'night'       : [ 'lantern:bright-white', 'door-entry:med-white' ],
  'nook'        : [ 'kitchen:off', 'kitchen-pendants:off', 'breakfast-nook:dim:30' ],
  'panic'       : [ 'all_on', 'sirens:on' ],
  'party'       : [  'bendy:@', 'breakfast-nook:dim:30', 'dining-chandelier:dim:25', 'family-room-left:dim:15', 
                     'family-room-right:dim:15', 'kitchen-pendants:dim:40', 'kitchen:dim:5', 'lounge:dim:15', 
                     'office:dim:20', 'window-lights:dim:30',
                     'accent-party:@', 'tree:@', 'twinkle:@', 'lightning:@' ],
  'leaving'     : [ 'away:@' ],
  'tv'          : [  'bendy:off', 'breakfast-nook:off', 'dining-chandelier:dim:25', 'family-room-left:dim:20', 
                     'family-room-right:dim:20', 'kitchen-pendants:dim:30', 'kitchen:off', 'lounge:dim:15', 
                     'office:dim:20', 'window-lights:off' ],
  'gh1'         : [ 'lantern:green', 'garage:dim-red', 'mobile-bulb:bulb-dim:2', 'garage-L:off', 'garage-R:off', 'out-sconce:off', 'out-front-moon:off' ],
  'gh0'         : [ 'lantern:white', 'garage:bulb-off', 'mobile-bulb:bulb-off', 'garage-L:on', 'garage-R:on', 'out-sconce:on', 'out-front-moon:on' ],

  # Groups (not fully set scenes; need target value to be provided by caller)
  # NB outside lights have mixed unit types; can't use group as values not all the same; see area-based.
  'bedrm'       : [ 'bedroom-entrance:@', 'bedroom-light:@' ],
  'fam'         : [ 'family-room-left:@', 'family-room-right:@', 'dining-chandelier:@' ],
  'kit'         : [ 'kitchen:@', 'kitchen-pendants:@', 'breakfast-nook:@' ],
  'inside'      : [ 'bedrm:@', 'fam:@', 'kit:@', 'main:@' ],
  'loungerm'    : [ 'bendy:@', 'lounge:@', 'window-lights:@', 'tp-dining-chandelier:@' ],
  'main'        : [ 'office:@', 'loungerm:@', 'kit:@', 'fam:@' ],
  'sirens'      : [ 'siren1:@', 'siren2:@', 'siren3:@' ],
  'accents'     : [ 'tp-color-sofa-left:@', 'tp-color-sofa-right:@', 'tp-color-moon:@', 'tp-color-stairs:@' ],
  'accents:off' : [ 'accents:bulb-off' ],
  'accents:on'  : [ 'accents:med-warm' ],

 # Homesec trigger reactions
  'all:off'     : [ 'all_off' ],
  'all:on'      : [ 'all_on' ],
  'all_on'      : [ 'inside:full', 'outside_full' ],
  'all_off'     : [ 'inside:off', 'outside_off', 'sirens:off' ],
  'sirens_on'   : [ 'sirens:on' ],
  'sirens_off'  : [ 'sirens:off' ],
  # red turned on for a few seconds when alarm triggered but not yet activated.
  'red:on'      : [ 'accents:red' ],
  'red:off'     : [ 'accents:bulb-off' ],
  # blue turned on for a few seconds when transitioning to state arming-away
  'blue:on'     : [ 'accents:blue' ],
  'blue:off'    : [ 'accents:bulb-off' ],
  # blue_special triggered on rcam1 motion when arm-home
  'blue_special:on'  : [],
  'blue_special:off' : [],
  # pony triggered by outside trigger when arm-away
  'pony:on'     : [ 'accents:orange' ],
  'pony:off'    : [ 'accents:bulb-off' ],

 # End-point names for web-based individual controls
  # Accent color lights (controlled by homesec)
  'accent-party:off'   : [ 'WEBS:home.point0.net/p0' ],
  'accent-party:on'    : [ 'WEBS:home.point0.net/p1' ],
  'tree:off'           : [ 'WEB:tree/0' ],
  'tree:on'            : [ 'WEB:tree/1' ],
  #
  # Outside lighting controller: pout*
  'out-all:off'        : [ 'landscaping:off' ],
  'out-all:on'         : [ 'landscaping:on' ],
  ## 'out-all:off'        : [ 'WEB:pout:8080/a0', 'WEB:pout2:8080/a0' ],
  ## 'out-all:on'         : [ 'WEB:pout:8080/a1', 'WEB:pout2:8080/a1' ],
  'out-monument:off'   : [ 'WEB:pout:8080/10' ],
  'out-monument:on'    : [ 'WEB:pout:8080/11' ],
  'out-sconce:off'     : [ 'WEB:pout:8080/20' ],
  'out-sconce:on'      : [ 'WEB:pout:8080/21' ],
  'out-front-path:off' : [ 'WEB:pout:8080/30' ],
  'out-front-path:on'  : [ 'WEB:pout:8080/31' ],
  'out-front-moon:off' : [ 'WEB:pout:8080/40' ],
  'out-front-moon:on'  : [ 'WEB:pout:8080/41' ],
  'out-front-up:off'   : [ 'WEB:pout:8080/50' ],
  'out-front-up:on'    : [ 'WEB:pout:8080/51' ],
  'out-maple:off'      : [ 'WEB:pout:8080/70' ],
  'out-maple:on'       : [ 'WEB:pout:8080/71' ],
  'out-magnolia:off'   : [ 'WEB:pout2:8080/10' ],
  'out-magnolia:on'    : [ 'WEB:pout2:8080/11' ],
  'out-holly:off'      : [ 'WEB:pout2:8080/20' ],
  'out-holly:on'       : [ 'WEB:pout2:8080/21' ],
  'out-arch:off'       : [ 'WEB:pout2:8080/30' ],
  'out-arch:on'        : [ 'WEB:pout2:8080/31' ],
  'out-back-moon:off'  : [ 'WEB:pout2:8080/40' ],

  # Effects: twinkle (firefly animations)
  'twinkle:off'        : [ 'WEB:twinkle/0' ],
  'twinkle:on'         : [ 'WEB:twinkle/1' ],
  # Effects: lightning
  'lightning:off'      : [ 'WEB:lightning/0' ],
  'lightning:on'       : [ 'WEB:lightning/f' ],
}

# --------------------------------------------------

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

# "Encryption" and Decryption of TP-Link Smart Home Protocol                                                        
# XOR Autokey Cipher with starting key = 171                                                                      

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


def find_hostname(in_unit):
  unit = in_unit if 'tp-' in in_unit else 'tp-' + in_unit
  try:
    if socket.gethostbyname(unit): return unit
  except Exception as e:
    pass
  sys.exit('Unknown target unit: %s' % in_unit)


def deep_replace(str_or_list, find, repl):
  if not isinstance(str_or_list, list):
    return str_or_list.replace(find, repl)
  return [i.replace(find, repl) for i in str_or_list]


def gen_command(search):
  if search.startswith('b-'): search = search.replace('b-', 'bulb-')
  #
  c = CMD_LOOKUP.get(search)
  if c: return c
  # Try a search with a parameterized key.
  if ':' in search:
    [search2, param] = search.split(':', 1)
    if param == '0' and search2 == 'dim':
      return CMD_LOOKUP[unit_type]['off']
    c = CMD_LOOKUP.get('%s:@@' % search2)
    if c: return deep_replace(c, '@@', param)
  raise Exception('Unknown command: %s' % search)


def send_tp_cmd(hostname, cmd, get_resp=True):
  if ARGS.debug: print('sending %s : %s' % (hostname, cmd))
  sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    sock_tcp.settimeout(ARGS.timeout)
    sock_tcp.connect((hostname, 9999))
    sock_tcp.send(encrypt(cmd))
  except Exception as e:
    msg = 'ERROR connecting to tplink host %s' % hostname
    if ARGS.debug:
      print(msg)
      raise
    else:
      syslog.syslog(syslog.LOG_ERR, msg)
      return msg
  if not get_resp: 
    sock_tcp.close()
    return 'sent'
  resp = sock_tcp.recv(2048)
  sock_tcp.close()
  out = decrypt(resp[4:])
  if ARGS.debug: print('response: %s' % out)
  return out


def process_web_request(addr, in_unit='web'):
  if in_unit == 'webs':
    host, path = addr.split('/', 1)
    url = 'https://' + host + ':8443/' + path
  else:
    url = 'http://' + addr
  try:
    r = requests.get(url, allow_redirects=True, timeout=ARGS.timeout)
  except Exception as e:
    return '[%s] exception: %s' % (url, e)
  if ARGS.debug: print('web request [%s] -> (%d): %s' % (url, r.status_code, r.text))
  if r.status_code != 200 and not r.text: return '[%s] status %s' % (url, r.status_code)
  return r.text


# get_resp => sync call and return responce.  Use False when need for speed (e.g. near parallel requests)
def control(in_unit, in_state, get_resp=True):
  if ARGS.debug: print('control request %s -> %s (resp? %s)' % (in_unit, in_state, get_resp))
  in_unit = in_unit.lower()
  in_state = in_state.lower()
  # Check for scene with different state support.
  scene_with_state = '%s:%s' % (in_unit, in_state)
  if scene_with_state in SCENE_LOOKUP: in_unit = scene_with_state
  # Check for scene logic
  if in_unit in SCENE_LOOKUP:
    resp = []
    for i in SCENE_LOOKUP[in_unit]:
      if ':' in i:
        unit, state = i.split(':', 1)
      else:
        unit, state = i, 'go'
      # Handle delay (when part of a scene expansion needs to override earlier parts)
      while unit[0] == '$':
        unit = unit[1:]
        time.sleep(2)
      if state == '@': state = in_state
      ans = control(unit, state, ARGS.debug)
      resp.append(ans)
      if ARGS.debug: print('%s(%s) returned: %s' % (unit, state, ans))
    return resp
  # Special substitutions
  if in_unit == 'breakfast-nook' and in_state == 'med': in_state = 'dim:30'
  # Handle web-based requests
  if in_unit.startswith('web'):
    return process_web_request(in_state, in_unit)
  # Assume in_unit is a hostanme (probably without the tp- prefix)
  hostname = find_hostname(in_unit)
  cmd = gen_command(in_state)
  #
  if ARGS.debug: print('%s:%s -> %s:%s' % (in_unit, in_state, hostname, cmd))
  if not isinstance(cmd, list):
    return send_tp_cmd(hostname, cmd, get_resp)
  resp = []
  for i in cmd:
    resp.append(send_tp_cmd(hostname, i, get_resp))
  return resp    


def main():
  ap = argparse.ArgumentParser(description='docker container launcher')
  ap.add_argument('--debug', '-d', action='store_true', help='output results and disable parallelism')
  ap.add_argument('--timeout', '-t', default=8, help='timeout in seconds')
  ap.add_argument('target', help='unit or scene to address')
  ap.add_argument('command', nargs='?', default='', help='command to send to that unit')
  args = ap.parse_args()
  global ARGS
  ARGS.debug = args.debug
  ARGS.timeout = args.timeout

  print(control(args.target, args.command))
  

if __name__ == '__main__':
  main()
