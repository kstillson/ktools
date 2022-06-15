
import itertools, pytest, os, shutil, sys

import context_hc  # fixes path
import kcore.varz as V   # this is where the test plugin stores it stuff.
import hc

SETTINGS = {
    'data_dir': ['testdata/home_control'],
    'debug': True,
    'plugins': ['plugin_test.py'],  # skip the other plugins...
}

@pytest.fixture(scope='session')
def init():
    # ----- setup

    # -- establish private.d contents
    priv_dir = 'testdata/home_control/private.d'
    priv_data = '%s/hcdata_private.py' % priv_dir
    os.mkdir(priv_dir)
    with open(priv_data, 'w') as f:
        f.write('''
PRIV_DEV = { 'priv-dev' : 'TEST:%d:%c' }
PRIV_SCENE = { 'priv-scene' : [ 'priv-dev' ] }
def init(devices, scenes): devices.update(PRIV_DEV); scenes.update(PRIV_SCENE); return devices, scenes
''')

    # -- Register our SETTINGS
    hc.reset()  # clear out any other test's initialization...
    hc.control('doesnt', 'matter', SETTINGS)

    yield  # ----- setup // teardown
    
    # -- clean-up private.d dir
    shutil.rmtree(priv_dir)
    
    
# ---------- general purpose helpers

def flatten(lol):   # lol = list of lists  ;-)
    if isinstance(lol, str): return [lol]
    if len(lol) == 1:
        result = flatten(lol[0]) if type(lol[0]) == list else lol
    elif type(lol[0]) == list: result = flatten(lol[0]) + flatten(lol[1:])
    else: result = [lol[0]] + flatten(lol[1:])
    return result

# ---------- assertion check helpers

def checkval(key, expected_value):
    assert V.get('TEST-' + key) == expected_value


def check(control_output, expect_in_output, key=None, expected_value=None):
    ok, output = control_output
    assert ok == ('ok' in expect_in_output)
    assert expect_in_output in output
    if key: checkval(key, expected_value)

    
def check_each(control_output, expect_in_each_output, key=None, expected_value=None):
    overall_ok, outputs = control_output
    flattened_outputs = flatten(outputs)
    if expect_in_each_output:
        for out in flattened_outputs: assert expect_in_each_output in out
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
    check_each(hc.control('trivial1', 'cmd1'),     'ok', 'host1', 'cmd1')

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

    # check that command-specific scene overrides a plain one
    check_each(hc.control('scene2', 'x'), 'ok')
    checkval('host1', 'x1')
    checkval('host2', 'x1')
    checkval('wildq', 'special-off')
    checkval('wild1-2', 'x')
        
    # check partially successful scene
    ok, outputs = hc.control('scene3', 'cmd4')
    assert not ok
    assert 'ok' in outputs[0]
    assert 'Dont know what to do with target deviceZ' == outputs[1]
    checkval('host1', 'cmd4')


def test_private_dir(init):
    check_each(hc.control('priv-scene', 'cmd5'),    'ok', 'priv-dev', 'cmd5')
