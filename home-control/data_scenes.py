
SCENES = {
 # Areas based groups and meta-groups
  'all'         : [ 'inside', 'outside' ],
  'bedrm'       : [ 'tp-bedroom-entrance', 'tp-bedroom-light' ],
  'fam'         : [ 'tp-family-room-left', 'tp-family-room-right', 'tp-dining-chandelier' ],
  'inside'      : [ 'bedrm', 'fam', 'kit', 'main' ],
  'office'      : [ 'tp-office' ],
  'outside'     : [ 'bulb-tp-door-entry', 'tp-landscaping', 'bulb-tp-lantern', 'tp-patio', 'tp-rear-flood' ],
  'kit'         : [ 'tp-kitchen', 'tp-kitchen-pendants', 'tp-breakfast-nook' ],
  'lng'         : [ 'tp-bendy', 'tp-lounge', 'tp-window-lights', 'tp-dining-chandelier' ],
  'main'        : [ 'fam', 'kit', 'lng', 'office' ],

 # Groupings by similar purpose    
  'sirens'      : [ 'siren1', 'siren2', 'siren3' ],
  'accents'     : [ 'bulb-tp-color-sofa-left', 'bulb-tp-color-sofa-right', 'bulb-tp-color-moon', 'bulb-tp-color-stairs' ],

 # Activity-based
  'away'        : [ 'main:off', 'delay:2:office:dim:40' ],
  'bedtime'     : [ 'inside:off', 'delay:2:tp-bedroom-light:dim:10' ],
  'comp'        : [ 'fam:off', 'kit:off', 'office:dim:55', 'lng:off' ],
  'cooking'     : [ 'tp-kitchen:dim:60', 'tp-kitchen-pendants:dim:60', 'tp-breakfast-nook:off' ],
  'home'        : [ 'office:med', 'lng:dim:30', 'tp-kitchen:dim:60', 'tp-dining-chandelier:dim:30' ],
  'panic'       : [ 'all', 'sirens' ],
  'panic:on'    : [ 'all:full', 'sirens:on' ],
  'party:on'    : [  'tp-bendy:on', 'tp-breakfast-nook:dim:30', 'tp-dining-chandelier:dim:25', 'tp-family-room-left:dim:15', 
                     'tp-family-room-right:dim:15', 'tp-kitchen-pendants:dim:40', 'tp-kitchen:dim:5', 'tp-lounge:dim:15', 
                     'tp-office:dim:20', 'tp-window-lights:dim:30',
                     'accent-party', 'tree', 'twinkle', 'lightning' ],
  'tv'          : [  'tp-bendy:off', 'tp-breakfast-nook:off', 'tp-dining-chandelier:dim:25', 'tp-family-room-left:dim:20', 
                     'tp-family-room-right:dim:20', 'tp-kitchen-pendants:dim:30', 'tp-kitchen:off', 'tp-lounge:dim:15', 
                     'tp-office:dim:20', 'tp-window-lights:off' ],
  'gh1'         : [ 'bulb-tp-lantern:green', 'bulb-tp-garage:dim-red', 'bulb-tp-mobile-bulb:bulb-dim:2', 'tp-garage-L:off', 'tp-garage-R:off', 'out-sconce:off', 'out-front-moon:off' ],
  'gh0'         : [ 'bulb-tp-lantern:white', 'bulb-tp-garage:bulb-off', 'bulb-tp-mobile-bulb:bulb-off', 'tp-garage-L:on', 'tp-garage-R:on', 'out-sconce:on', 'out-front-moon:on' ],

 # Aliases
  'down-dim'    : [ 'main:dim' ],
  'leaving'     : [ 'away' ],

 # homesec custom actions
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
}


def init(devices, scenes):
  scenes.update(SCENES)
  return devices, scenes
