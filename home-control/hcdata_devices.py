
DEVICES = {

# ---------- tplink generics

    # The 'BULB-' and 'PLUG-' prefixes are plugin type 'hints' that allow us
    # to differenciate TP-Link device types by artificially introducing the
    # prefix into the device names.  The plugin will strip out these hint
    # prefixes before using the device-name as an actual hostname.

  'BULB-tp-*'         : 'TPLINK-BULB:%d:%c',
  'PLUG-tp-*'         : 'TPLINK-PLUG:%d:%c',
  'tp-*'              : 'TPLINK:%d:%c',

# ---------- tplink individual device overrides and aliases

  'tp-office:dim'     : 'TPLINK:tp-office:dim:50',
    
# ---------- delay trigger

  'delay'             : 'DELAY:%c',

# ---------- web-based

# End-point names for web-based individual controls
  # Accent color lights (controlled by homesec)
  'accent-party:off'   : 'WEBS:home.point0.net/p0',
  'accent-party:on'    : 'WEBS:home.point0.net/p1',
  'tree:off'           : 'WEB:neotree2/0',
  'tree:on'            : 'WEB:neotree2/1',
  #
  # Outside lighting controller: pout*
  ## 'out-all:off'        : 'WEB:pout:8080/a0', 'WEB:pout2:8080/a0',
  ## 'out-all:on'         : 'WEB:pout:8080/a1', 'WEB:pout2:8080/a1',
  'out-monument:off'   : 'WEB:pout:8080/10',
  'out-monument:on'    : 'WEB:pout:8080/11',
  'out-sconce:off'     : 'WEB:pout:8080/20',
  'out-sconce:on'      : 'WEB:pout:8080/21',
  'out-front-path:off' : 'WEB:pout:8080/30',
  'out-front-path:on'  : 'WEB:pout:8080/31',
  'out-front-moon:off' : 'WEB:pout:8080/40',
  'out-front-moon:on'  : 'WEB:pout:8080/41',
  'out-front-up:off'   : 'WEB:pout:8080/50',
  'out-front-up:on'    : 'WEB:pout:8080/51',
  'out-maple:off'      : 'WEB:pout:8080/70',
  'out-maple:on'       : 'WEB:pout:8080/71',
  'out-magnolia:off'   : 'WEB:pout2:8080/10',
  'out-magnolia:on'    : 'WEB:pout2:8080/11',
  'out-holly:off'      : 'WEB:pout2:8080/20',
  'out-holly:on'       : 'WEB:pout2:8080/21',
  'out-arch:off'       : 'WEB:pout2:8080/30',
  'out-arch:on'        : 'WEB:pout2:8080/31',
  'out-back-moon:off'  : 'WEB:pout2:8080/40',

  # Effects: twinkle (firefly animations)
  'twinkle:off'        : 'WEB:twinkle/0',
  'twinkle:on'         : 'WEB:twinkle/1',
  # Effects: lightning
  'lightning:off'      : 'WEB:lightning/0',
  'lightning:on'       : 'WEB:lightning/f',
}


def init(devices, scenes):
    devices.update(DEVICES)
    return devices, scenes
