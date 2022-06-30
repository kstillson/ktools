
DEVICES = {
    # for test_plugins.py
    'device1'     : 'TEST:host1:%c',
    'device2'     : 'TEST:host2:%c',
    'device2:off' : 'TEST:host2:special-off',
    'wild1-*'     : 'TEST:%d:%c',
    'wild*:off'   : 'TEST:%d:special-%c',
    'deviceX'     : 'INVALID:what:ever',

    # for test_web_plugin.py
    # Note that the command (%c) is being used both as the port number and
    # the path.  This is so that the test can pick a random high port and
    # communicate to this directive what port to use through %c.
    'web1'        : 'WEB:localhost:%c/%c',
}


def init(devices, scenes):
    devices.update(DEVICES)
    return devices, scenes
