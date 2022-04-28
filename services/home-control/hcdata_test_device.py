
DEVICES = {
    'test-device': 'TEST:%d:%c'
}


def init(devices, scenes):
    devices.update(DEVICES)
    return devices, scenes
