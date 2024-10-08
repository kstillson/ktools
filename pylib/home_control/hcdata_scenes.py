
'''Example SCENES dictionary.  You'll want to customize your own.

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
  'bedrm'       : [ 'bedroom-entrance', 'bedroom-light' ],
  'fam'         : [ 'family-room-left', 'family-room-right', 'dining-chandelier' ],
  'inside'      : [ 'bedrm', 'fam', 'kit', 'main' ],
  'landscaping' : [ 'out-front', 'out-back' ],
  'out'         : [ 'door-entry', 'lantern', 'landscaping' ],
  'out2'        : [ 'out', 'patio' ],
  'outside'     : [ 'out2', 'rear-flood' ],
  'kit'         : [ 'kitchen', 'kitchen-pendants', 'breakfast-nook' ],
  'lng'         : [ 'bendy', 'lounge', 'window-lights', 'lounge-chandelier' ],
  'main'        : [ 'fam', 'kit', 'lng', 'office' ],
  # aliases
  'ofc'         : [ 'office' ],
  'out-back'    : [ 'pout2' ],

 # Groupings by similar purpose
  'accents'     : [ 'color-sofa-left', 'color-sofa-right', 'color-moon', 'color-stairs' ],
  'sirens'      : [ 'siren1', 'siren2', 'siren3' ],
  'specials'    : [ 'accents', 'neotree', 'twinkle', 'lightning' ],

   # (used in redblue animation by ulb/panic)
  'rb1'         : [ 'color-sofa-left', 'color-stairs', 'lantern' ],
  'rb2'         : [ 'color-sofa-right', 'color-moon', 'door-entry' ],

 # Activity-based
  'away'        : [ 'main:off', 'delay:2:office:dim:40' ],
  'bedtime'     : [ 'inside:off', 'pout2:off', 'delay:2:bedroom-light:dim:10' ],
  'comp'        : [ 'fam:off', 'kit:off', 'office:dim:55', 'lng:off' ],
  'cooking'     : [ 'kitchen:dim:60', 'kitchen-pendants:dim:60', 'breakfast-nook:off' ],
  'gh0'         : [ 'lantern:bright-warm', 'garage:bulb-off', 'mobile-bulb:bulb-off', 'garage-L:on', 'garage-R:on', 'out-sconce:on', 'out-front-moon:on' ],
  'gh1'         : [ 'lantern:green', 'garage:dim-red', 'mobile-bulb:bulb-dim:2', 'garage-L:off', 'garage-R:off', 'out-sconce:off', 'out-front-moon:off' ],
  'home'        : [ 'office:med', 'lng:dim:30', 'kitchen:dim:60', 'dining-chandelier:dim:30' ],
  'nook'        : [ 'kitchen:dim', 'kitchen-pendants:dim', 'breakfast-nook:dim:33' ],
  'panic'       : [ 'all', 'sirens' ],
  'party'       : [  'bendy', 'breakfast-nook', 'dining-chandelier', 'family-room-left',
                     'family-room-right', 'kitchen-pendants', 'kitchen', 'lounge',
                     'office', 'window-lights', 'accents-party', 'neotree', 'twinkle', 'lightning' ],
  'tv'          : [  'bendy:off', 'breakfast-nook:off', 'dining-chandelier:dim:25', 'family-room-left:dim:20',
                     'family-room-right:dim:20', 'kitchen-pendants:dim:30', 'kitchen:off', 'lounge:dim:15',
                     'office:dim:20', 'window-lights:off' ],
  'warmer'      : [ 'space-heater:on', 'delay:900:space-heater:off' ],

 # Special command-specific overrides
  'accents:party': [ 'accents-party:on' ],
  'blue:on'     : [ 'accents:blue' ],
  'panic:on'    : [ 'all:full', 'sirens:on' ],
  'party:on'    : [  'bendy:on', 'breakfast-nook:dim:25', 'dining-chandelier:dim:25', 'family-room-left:dim:15',
                     'family-room-right:dim:15', 'kitchen-pendants:dim:40', 'kitchen:dim:5', 'lounge:dim:15',
                     'office:dim:20', 'window-lights:dim:30',
                     'accents-party', 'neotree', 'twinkle', 'lightning' ],
  ##
  'red:go'      : [ 'main:off', 'red:on' ],
  'red:dim'     : [ 'main:dim', 'red:on' ],
  'red:med'     : [ 'main:med', 'red:on' ],
  'red:stop'    : [ 'main:med', 'red:off' ],
  #
  'redweb:red'  : [ 'web:lightning/red', 'web:trellis2/red', 'web:twinkle/red' ],
  'redweb:off'  : [ 'web:lightning/off', 'web:trellis2/off', 'web:twinkle/off' ],
  #
  'red:on'      : [ 'accents:red', 'door-entry:red', 'lantern:blue', 'redweb:red' ],
  'red:off'     : [ 'accents:bulb-off', 'door-entry:white', 'lantern:bright-warm', 'redweb:off' ],

 # Scene aliases
  'blue'        : [ 'accents:blue' ],
  'down-dim'    : [ 'main:dim' ],
  'leaving'     : [ 'away' ],

 # Shorthand aliases (intended for cli use)
  '00'          : [ 'all:off' ],
  '0'           : [ 'inside:off' ],
  '1'           : [ 'inside:dim' ],
  '5'           : [ 'inside:med' ],
  '9'           : [ 'inside:full' ],
  '911'         : [ 'panic' ],
  'b'           : [ 'bedtime' ],
  'c'           : [ 'comp' ],
  'k'           : [ 'kitchen' ],
  'l'           : [ 'landscaping' ],
  'O'           : [ 'office' ],
  'o'           : [ 'outside' ],

# Special dynamically expanded
  'TP'          : [ '$PLUGIN_NAME:TPLINK*' ],
}


# When this file is loaded by hc.py, it runs init() to return added data.
def init(devices, scenes):
  scenes.update(SCENES)
  return devices, scenes
