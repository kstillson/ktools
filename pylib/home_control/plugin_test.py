'''home-control plugin for testing purposes

This plugin takes its params as a key-value pair and stores them into varz.
So, for example, if you create a device: { 'device1': 'TEST:%d:%c' } and then
call hc.control('device1', 'command1'), a varz key 'TEST-device1' will be
created with the valud 'command1' will be set.

Essentially varz is being used as a global singleton datastore to provide
communication between components of the system.
'''

import sys
import kcore.varz as V

def init(settings):
    return ['TEST']


def control(plugin_name, plugin_params, device_name, command):
    key, value = plugin_params.split(':')
    key = 'TEST-' + key.replace('%d', device_name)
    value = value.replace('%c', command)
    print(f'TEST PLUGIN [params:{plugin_params}] : {key} -> {value}', file=sys.stderr)
    if 'BAD' in value: return False, f'{device_name}: bad value'
    V.set(key, value)
    return True, f'TEST({key}, {value}): ok'
