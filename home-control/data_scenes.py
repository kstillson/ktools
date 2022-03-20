
SCENES = {
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


  'out-all:off'        : 'landscaping:off',
  'out-all:on'         : 'landscaping:on',

    
}


def init(devices, scenes):
    scenes.update(SCENES)
    return devices, scenes
