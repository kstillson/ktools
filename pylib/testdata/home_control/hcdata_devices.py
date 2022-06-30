
DEVICES = {
    # for test_plugins.py
    'device1'     : 'TEST:host1:%c',
    'device2'     : 'TEST:host2:%c',
    'device2:off' : 'TEST:host2:special-off',
    'wild1-*'     : 'TEST:%d:%c',
    'wild*:off'   : 'TEST:%d:special-%c',
    'deviceX'     : 'INVALID:what:ever',

    # for test_web_plugin.py
    'web1'        : 'WEB:localhost:62312/%c',
}


def init(devices, scenes):
    devices.update(DEVICES)
    return devices, scenes
