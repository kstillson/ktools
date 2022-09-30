
'''Example DEVICES dictionary.  You'll want to customize your own.

In its simplest form, the DEVICES dict maps from device names (which can be
arbitrary strings, although often match up to physical device DNS names) to
name of the plugin responsible for processing commands for each device.  But
it's usually a little more complicated than that..

Each Python file that provides a plugin implementation can register multiple
plugin names for itself; all registered names get routed to that same plugin.
The plugin is told which plugin name led to a particular invocation, so the
plugin can provide diferent flavors of operation based on plugin name.  For
example, in the configuration below, the TpLink plugin supports smart plugs,
smart bulbs, and smart switches.

In addition, plugin calls can provide parameters-- whatever is to the right of
the first ":" after tha plugin name, on the RHS of the dict.  The special
characters '%d' will be replaced by the name of the device which triggered the
plugin invocation, and '%c' will be replaced by the command the user wanted to
execute on the device.  So, for example, if a user called
hc.control('PLUG-tp-plug1', 'on'), then the framework would eventually call
plugin_tplink.control(plugin_name='TPLINK-PLUG', plugin_params='%d:%c',
                      device_name='PLUG-tp-plug1', device_command='on')

To make things even more flexible (yes, flexible, no, not confusing.. ;-) the
LHS of the dict can also have the form 'device:command'.  In other words, you
have multiple entries for the same device that use different plugin params (or
even different plugins entirely, if you want), based on the command.  As you
can see below, this is most useful when you want to translate different
commands into different web get-requests, and don't want to hard-code the
translation table into the plugin.
'''


DEVICES = {

    # ---------- tplink devices

    # Note that my hostnames are the same as my device string names, except the hostnames
    # have a leading "tp-", which is added here.

    'bedroom-entrance'		: 'TPLINK-SWITCH:tp-%d:%c',
    'bedroom-light'		: 'TPLINK-SWITCH:tp-%d:%c',
    'bendy'			: 'TPLINK-PLUG:tp-%d:%c',
    'breakfast-nook'		: 'TPLINK-SWITCH:tp-%d:%c',
    'color-moon'		: 'TPLINK-BULB:tp-%d:%c',
    'color-sofa-left'		: 'TPLINK-BULB:tp-%d:%c',
    'color-sofa-right'		: 'TPLINK-BULB:tp-%d:%c',
    'color-stairs'		: 'TPLINK-BULB:tp-%d:%c',
    'crawlspace'		: 'TPLINK-PLUG:tp-%d:%c',
    'dining-chandelier'		: 'TPLINK-SWITCH:tp-%d:%c',
    'door-entry'		: 'TPLINK-BULB:tp-%d:%c',
    'family-room-left'		: 'TPLINK-SWITCH:tp-%d:%c',
    'family-room-right'		: 'TPLINK-SWITCH:tp-%d:%c',
    'garage'			: 'TPLINK-BULB:tp-%d:%c',
    'garage-L'			: 'TPLINK-PLUG:tp-%d:%c',
    'garage-R'			: 'TPLINK-PLUG:tp-%d:%c',
    'kitchen'			: 'TPLINK-SWITCH:tp-%d:%c',
    'kitchen-pendants'		: 'TPLINK-SWITCH:tp-%d:%c',
    'landscaping'		: 'TPLINK-PLUG:tp-%d:%c',
    'lantern'			: 'TPLINK-BULB:tp-%d:%c',
    'lounge'			: 'TPLINK-SWITCH:tp-%d:%c',
    'lounge-chandelier'		: 'TPLINK-SWITCH:tp-%d:%c',
    'mobile-bulb'		: 'TPLINK-BULB:tp-%d:%c',
    'office'			: 'TPLINK-SWITCH:tp-%d:%c',
    'patio'			: 'TPLINK-PLUG:tp-%d:%c',
    'rear-flood'		: 'TPLINK-PLUG:tp-%d:%c',
    'siren1'			: 'TPLINK-PLUG:tp-%d:%c',
    'siren2'			: 'TPLINK-PLUG:tp-%d:%c',
    'siren3'			: 'TPLINK-PLUG:tp-%d:%c',
    'space-heater'		: 'TPLINK-PLUG:tp-%d:%c',
    'tree'			: 'TPLINK-PLUG:tp-%d:%c',
    'window-lights'		: 'TPLINK-SWITCH:tp-%d:%c',

    # ---------- tplink individual device overrides and aliases

    'office:dim'     : 'TPLINK-SWITCH:tp-office:dim:40',

    # ---------- delay trigger

    'delay'             : 'DELAY:%c',

    # ---------- web-based

    # End-point names for web-based individual controls
    # Accent color lights (controlled by homesec)
    'accent-party:off'   : 'WEBS:home.point0.net/p0',
    'accent-party:on'    : 'WEBS:home.point0.net/p1',
    'neotree:off'        : 'WEB:neotree2/0',
    'neotree:on'         : 'WEB:neotree2/1',
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


# When this file is loaded by hc.py, it runs init() to return added data.
def init(devices, scenes):
    devices.update(DEVICES)
    return devices, scenes
