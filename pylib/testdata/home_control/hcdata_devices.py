
DEVICES = {
    'device1'     : 'TEST:host1:%c',
    'device2'     : 'TEST:host2:%c',
    'device2:off' : 'TEST:host2:special-off',
    'wild1-*'     : 'TEST:%d:%c',
    'wild*:off'   : 'TEST:%d:special-%c',
    'deviceX'     : 'INVALID:what:ever',
}


def init(devices, scenes):
    devices.update(DEVICES)
    return devices, scenes
