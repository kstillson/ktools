
import sys

VALUES = {}

def init(settings):
    global SETTINGS, VALUES
    settings['TEST_VALS'] = VALUES  # for visibility to unit tests.
    return ['TEST']


def control(plugin_name, plugin_params, device_name, command):
    global VALUES
    key, value = plugin_params.split(':')
    key = key.replace('%d', device_name)
    value = value.replace('%c', command)
    print(f'TEST PLUGIN [params:{plugin_params}] : {key} -> {value}', file=sys.stderr)
    if value == 'BAD': return f'{device_name}: bad value'
    VALUES[key] = value
    return f'{device_name}: ok'
