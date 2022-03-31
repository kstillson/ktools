
import pytest, sys

import context_hc  # adds .. to the path
import hc

TEST_SETTINGS = {
    'data-dir': 'testdata',
    'debug': True,
    'plugins-dir': 'testdata',
}

@pytest.fixture(scope='session')
def init():
    # Register our TEST_SETTINGS dict with hc.  This has the side-effect of hc
    # using this dict for all subsequently set settings.  Once
    # plugin_test.init() is called, this will give us visibility into
    # TEST_SETTINGS['TEST_VALS'],
    hc.reset()  # clear out any other test's initialization...
    hc.control('doesnt', 'matter', TEST_SETTINGS)

    
# ---------- general purpose helpers

def flatten(lol):   # lol = list of lists  ;-)
    if len(lol) == 1:
        result = flatten(lol[0]) if type(lol[0]) == list else lol
    elif type(lol[0]) == list: result = flatten(lol[0]) + flatten(lol[1:])
    else: result = [lol[0]] + flatten(lol[1:])
    return result

# ---------- assertion check helpers

def checkval(key, expected_value):
    assert TEST_SETTINGS['TEST_VALS'][key] == expected_value


def check(output, expect_in_output, key=None, expected_value=None):
    assert expect_in_output in output
    if key: checkval(key, expected_value)

    
def check_each(outputs, expect_in_outputs, key=None, expected_value=None):
    flattened_outputs = flatten(outputs)
    for out in flattened_outputs: assert expect_in_outputs in out
    if key: checkval(key, expected_value)

    
# ---------- the tests

def test_delay_plugin(init):
    check(hc.control('device1', 'off'),  'ok', 'host1', 'off')

