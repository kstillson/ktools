
'''Example SCENES dictionary.  You'll want to support your own.

A scene is simply a fake device name that is replaced by a list of real
devices, or other scenes.

For example, with the data below, if the call hc.control('all', 'on') was
sent, it would be translated into an 'on' command for both 'inside' and
'outside'.  Both 'inside' and 'outside' are themselves scenes, so this
expansion continues recursively until all scenes are resolved into real
devices.

By default, whatever command is given to the scene will be passed down to each
of its expanded contents.  However, the RHS elements can specify override
commands for their devices.  For example, with the data below, if the device
'away' receives any command, the scene 'main' is turned 'off' and the scene
'office' is set to 'dim:40' after a 2 second delay.  Because both elements of
'away' override their commands on the RHS, the command that was originally
sent to 'away' is actually irrelevant.

In addition, the LHS can be command-specific.  This is useful for several
different cases.  In the data below, you can see that 'red:on' is translated
to 'accents:red', whereas the undecorated scene-name 'red' is translated to
just 'accents'.  Why?  The command 'red:off' is fine to translate to
'accents:off', but if 'red:on' were left alone, it would translate to
'accents:on' (rather than 'accents:red'), and the accent lights would just go
on to whatever color was last used, which might not be red.  Similarly, you
can see that the scene 'party:on' passes the 'on' command to some of its
expansion scenes & devices, but in other cases overrides 'on', translating it to
things like specific dimming levels.

'''

SCENES = {
 # Areas based groups and meta-groups
  'all'         : [ 'inside', 'outside' ],
  'bedrm'       : [ 'tp-bedroom-entrance', 'tp-bedroom-light' ],
  'fam'         : [ 'tp-family-room-left', 'tp-family-room-right', 'tp-dining-chandelier' ],
  'inside'      : [ 'bedrm', 'fam', 'kit', 'main' ],
  'office'      : [ 'tp-office' ],
  'outside'     : [ 'BULB-tp-door-entry', 'PLUG-tp-landscaping', 'BULB-tp-lantern', 'PLUG-tp-patio', 'PLUG-tp-rear-flood' ],
  'kit'         : [ 'tp-kitchen', 'tp-kitchen-pendants', 'tp-breakfast-nook' ],
  'lng'         : [ 'PLUG-tp-bendy', 'tp-lounge', 'tp-window-lights', 'tp-lounge-chandelier' ],
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
  'nook'        : [ 'tp-kitchen:off', 'tp-kitchen-pendants:off', 'tp-breakfast-nook:dim:30' ],
  'panic'       : [ 'all', 'sirens' ],
  'party'       : [  'PLUG-tp-bendy', 'tp-breakfast-nook', 'tp-dining-chandelier', 'tp-family-room-left',
                     'tp-family-room-right', 'tp-kitchen-pendants', 'tp-kitchen', 'tp-lounge',
                     'tp-office', 'tp-window-lights', 'accent-party', 'tree', 'twinkle', 'lightning' ],
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

 # Shorthand aliases (for cli use)
  '00'          : [ 'all:off' ],
  '0'           : [ 'inside:off' ],
  '1'           : [ 'inside:dim' ],
  '5'           : [ 'inside:med' ],
  '9'           : [ 'inside:full' ],
  '911'         : [ 'panic' ],
  'b'           : [ 'bedtime' ],
  'c'           : [ 'comp' ],
  'k'           : [ 'kitchen' ],
  'o'           : [ 'outside' ],
  'O'           : [ 'office' ],
}


# When this file is loaded by hc.py, it runs init() to return added data.
def init(devices, scenes):
  scenes.update(SCENES)
  return devices, scenes
