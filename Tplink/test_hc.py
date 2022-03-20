
import itertools, pytest, os, sys

os.environ['DATA_DIR'] = 'testdata'
os.environ['PLUGINS_DIR'] = 'testdata'
import hc

# plugin_test.init() will modified this dict by our session fixture,
# adding the key 'TEST_VALS', which provides us visibility into plugin ops.
SETTINGS = {}


@pytest.fixture(scope='session')
def init():
    print('@@ fixture', file=sys.stderr)
    hc.control('doesnt', 'matter', SETTINGS)

    
# ---------- general purpose helpers

def flatten(lol):   # lol = list of lists  ;-)
    if len(lol) == 1:
        result = flatten(lol[0]) if type(lol[0]) == list else lol
    elif type(lol[0]) == list: result = flatten(lol[0]) + flatten(lol[1:])
    else: result = [lol[0]] + flatten(lol[1:])
    return result

# ---------- assertion check helpers

def checkval(key, expected_value):
    assert SETTINGS['TEST_VALS'][key] == expected_value


def check(output, expect_in_output, key=None, expected_value=None):
    assert expect_in_output in output
    if key: checkval(key, expected_value)

    
def check_each(outputs, expect_in_outputs, key=None, expected_value=None):
    flattened_outputs = flatten(outputs)
    for out in flattened_outputs: assert expect_in_outputs in out
    if key: checkval(key, expected_value)

    
# ---------- the tests

def test_direct_device_control(init):
    check(hc.control('device1', 'off'),  'ok', 'host1', 'off')

    # Implicit "on" command and default settings.
    check(hc.control('device1'),  'ok', 'host1', 'on')

    # Unusual (but valid) command
    check(hc.control('device2', 'dim:50'),  'ok', 'host2', 'dim:50')

    # Command-specific device lookup for device2
    check(hc.control('device2', 'off'),  'ok', 'host2', 'special-off')

    # Invalid command (i.e. plugin rejected)
    check(hc.control('device2', 'BAD'),  'bad value', 'host2', 'special-off')

    # Basic wildcard match
    check(hc.control('wild1-x', 'funky'),  'ok', 'wild1-x', 'funky')

    # Command-specific wildcard overrides a general one
    check(hc.control('wild1-x', 'off'),  'ok', 'wild1-x', 'special-off')

    # Known device that runs an unknown plugin
    check(hc.control('deviceX'),  'INVALID not found')

    # Unmatched device name
    check(hc.control('deviceZ'),  'Dont know what to do with target')


def test_scenes(init):
    # trivial scene that just relays a command to device1.
    check_each(hc.control('trivial1', 'cmd1'),  'ok', 'host1', 'cmd1')

    # trivial scene that always turns device1 off.
    check_each(hc.control('trivial2'),             'ok', 'host1', 'off')
    check_each(hc.control('trivial2', 'whatever'), 'ok', 'host1', 'off')

    # simple scene that relays comamnd to two devices
    check_each(hc.control('scene1', 'cmd2'),       'ok', 'host1', 'cmd2')
    checkval('host2', 'cmd2')

    # recursive and a command-specific wildcard with a scene-overriden command
    check_each(hc.control('scene2', 'cmd3'),       'ok', 'host1', 'cmd3')
    checkval('host2', 'cmd3')
    checkval('wildq', 'special-off')
    
    # check partially successful scene
    outputs = hc.control('scene3', 'cmd4')
    assert 'device1: ok' == outputs[0]
    assert 'Dont know what to do with target deviceZ' == outputs[1]
    checkval('host1', 'cmd4')


def test_private_dir():
    check_each(hc.control('priv-scene', 'cmd5'),    'ok', 'priv-dev', 'cmd5')
