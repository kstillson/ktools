
'''Dummy device to activate the TEST plugin.

Please leave this in-place, it's used by unit testing and Docker self-testing.'''

DEVICES = {
    'test-device': 'TEST:%d:%c'
}


# When this file is loaded by hc.py, it runs init() to return added data.
def init(devices, scenes):
    devices.update(DEVICES)
    return devices, scenes
