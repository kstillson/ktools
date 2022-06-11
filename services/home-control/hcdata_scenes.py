
SCENES = {
 # Areas based groups and meta-groups
  'all'         : [ 'inside', 'outside' ],
  'bedrm'       : [ 'tp-bedroom-entrance', 'tp-bedroom-light' ],
  'fam'         : [ 'tp-family-room-left', 'tp-family-room-right', 'tp-dining-chandelier' ],
  'inside'      : [ 'bedrm', 'fam', 'kit', 'main' ],
  'office'      : [ 'tp-office' ],
  'outside'     : [ 'BULB-tp-door-entry', 'tp-landscaping', 'BULB-tp-lantern', 'tp-patio', 'tp-rear-flood' ],
  'kit'         : [ 'tp-kitchen', 'tp-kitchen-pendants', 'tp-breakfast-nook' ],
  'lng'         : [ 'PLUG-tp-bendy', 'tp-lounge', 'tp-window-lights', 'tp-dining-chandelier' ],
  'main'        : [ 'fam', 'kit', 'lng', 'office' ],

 # Groupings by similar purpose    
  'sirens'      : [ 'tp-siren1', 'tp-siren2', 'tp-siren3' ],
  'accents'     : [ 'BULB-tp-color-sofa-left', 'BULB-tp-color-sofa-right', 'BULB-tp-color-moon', 'BULB-tp-color-stairs' ],

 # Activity-based
  'away'        : [ 'main:off', 'delay:2:office:dim:40' ],
  'bedtime'     : [ 'inside:off', 'delay:2:tp-bedroom-light:dim:10' ],
  'comp'        : [ 'fam:off', 'kit:off', 'office:dim:55', 'lng:off' ],
  'cooking'     : [ 'tp-kitchen:dim:60', 'tp-kitchen-pendants:dim:60', 'tp-breakfast-nook:off' ],
  'gh0'         : [ 'BULB-tp-lantern:white', 'BULB-tp-garage:bulb-off', 'BULB-tp-mobile-bulb:bulb-off', 'tp-garage-L:on', 'tp-garage-R:on', 'out-sconce:on', 'out-front-moon:on' ],
  'gh1'         : [ 'BULB-tp-lantern:green', 'BULB-tp-garage:dim-red', 'BULB-tp-mobile-bulb:bulb-dim:2', 'tp-garage-L:off', 'tp-garage-R:off', 'out-sconce:off', 'out-front-moon:off' ],
  'home'        : [ 'office:med', 'lng:dim:30', 'tp-kitchen:dim:60', 'tp-dining-chandelier:dim:30' ],
  'panic'       : [ 'all', 'sirens' ],
  'party'       : [  'PLUG-tp-bendy', 'tp-breakfast-nook', 'tp-dining-chandelier', 'tp-family-room-left', 
                     'tp-family-room-right', 'tp-kitchen-pendants', 'tp-kitchen', 'tp-lounge', 
                     'tp-office', 'tp-window-lights', 'accent-party', 'tree', 'PLUG-tp-tree', 'twinkle', 'lightning' ],
  'tv'          : [  'PLUG-tp-bendy:off', 'tp-breakfast-nook:off', 'tp-dining-chandelier:dim:25', 'tp-family-room-left:dim:20', 
                     'tp-family-room-right:dim:20', 'tp-kitchen-pendants:dim:30', 'tp-kitchen:off', 'tp-lounge:dim:15', 
                     'tp-office:dim:20', 'tp-window-lights:off' ],
  'warmer'      : [ 'PLUG-tp-space-heater:on', 'delay:900:PLUG-tp-space-heater:off' ],

 # Special command-specific overrides
  'blue:on'     : [ 'accents:blue' ],
  'panic:on'    : [ 'all:full', 'sirens:on' ],
  'party:on'    : [  'PLUG-tp-bendy:on', 'tp-breakfast-nook:dim:30', 'tp-dining-chandelier:dim:25', 'tp-family-room-left:dim:15', 
                     'tp-family-room-right:dim:15', 'tp-kitchen-pendants:dim:40', 'tp-kitchen:dim:5', 'tp-lounge:dim:15', 
                     'tp-office:dim:20', 'tp-window-lights:dim:30',
                     'accent-party', 'tree', 'PLUG-tp-tree', 'twinkle', 'lightning' ],
  'red:on'     : [ 'accents:red' ],
  
 # Scene aliases
  'blue'        : [ 'accents' ],
  'down-dim'    : [ 'main:dim' ],
  'leaving'     : [ 'away' ],
  'red'         : [ 'accents' ],
}


def init(devices, scenes):
  scenes.update(SCENES)
  return devices, scenes
