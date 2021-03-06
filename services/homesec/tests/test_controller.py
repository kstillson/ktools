
import context_homesec     # fix path to includes work as expected in tests

import datetime, os, shutil, sys, tempfile, time

import kcore.common as common

import pytest
import model as M
import controller as C


# Replace ext module with its testing mock.
import ext_mock
C.ext = ext_mock

# ---------- testing infrastructure

@pytest.fixture(scope='module')
def setup_test():
    # Log to stdout (for easier test debugging)
    common.init_log('debug log', '-', filter_level_logfile=common.DEBUG)

    # Test-friendly timing changes.
    C.model.data.CONSTANTS['ALARM_TRIGGERED_DELAY'] = 1
    C.model.data.CONSTANTS['ALARM_DURATION'] = 1

    # Copy over test data
    tmpdir = tempfile.mkdtemp()
    dest = tmpdir + '/test-partition-state.data'
    shutil.copyfile('tests/test-partition-state.data', dest)
    C.model.data.PARTITION_STATE.filename = dest
    C.model.data.PARTITION_STATE.cache = None

    dest = tmpdir + '/test-touch.data'
    shutil.copyfile('tests/test-touch.data', dest)
    C.model.data.TOUCH_DATA.filename = dest
    C.model.data.TOUCH_DATA.cache = None

    yield tmpdir
    shutil.rmtree(tmpdir)


def wait_for_state(state, partition='default', samples=8, delay=0.2):
    for i in range(samples):
        seen = M.get_state(partition)
        if seen == state: return True
        time.sleep(delay)
    print(f'Wanted state {state} but it is still {seen}', file=sys.stderr)
    return False


# ---------- tests

def test_typical_sequence(setup_test):
    # One of the two users is home, and our partition state is arm-auto,
    # so that should resolve to arm-home.
    assert C.get_statusz_state() == 'arm-home(auto)/away/home'

    # Last user leaves and arm-auto -> away.
    fake_request_dict = { 'user': 'ken' }
    status, tracking = C.run_trigger(fake_request_dict, 'touch-away')
    assert status == 'ok'
    assert tracking == {
        'action': 'touch-away',
        'params': '%P',
        'partition': 'default',
        'partition_start_state': 'arm-auto',
        'speak': 'homesec armed',
        'state': 'arm-home',
        'trigger': 'touch-away',
        'trigger_friendly': None,
        'trigger_param': None,
        'zone': 'default',
        'user': 'ken', }
    assert C.get_statusz_state() == 'arm-away(auto)/away/away'
    assert ext_mock.LAST == "status = ext.read_web('http://hs-mud:8080/update?' + statusz_after)"
    assert ext_mock.LAST_ARGS[0] == 'http://hs-mud:8080/update?arm-away(auto)/away/away'

    # An outside trigger has no effect.
    status, tracking = C.run_trigger(fake_request_dict, 'motion_outside')
    assert status == 'ok'
    assert tracking['action'] == 'pass'
    assert C.get_statusz_state() == 'arm-away(auto)/away/away'
    # A duplicate trigger is squelched.
    status, tracking = C.run_trigger(fake_request_dict, 'motion_outside')
    assert status == 'squelched'

    # A default trigger raises the alarm.
    status, tracking = C.run_trigger(fake_request_dict, 'front_door')
    assert status == 'ok'
    assert tracking['action'] == 'state-delay-trigger'
    assert tracking['state'] == 'alarm-triggered'
    assert ext_mock.LAST == "status = ext.read_web('http://hs-mud:8080/update?' + statusz_after)"
    assert ext_mock.LAST_ARGS[0] == 'http://hs-mud:8080/update?alarm-triggered/away/away'

    assert wait_for_state('alarm')
    assert C.get_statusz_state() == 'alarm/away/away'

    assert wait_for_state('arm-auto')
    time.sleep(0.5)  # Give time for state change routines to finish up.
    assert C.get_statusz_state() == 'arm-away(auto)/away/away'
    assert ext_mock.LAST == "status = ext.read_web('http://hs-mud:8080/update?' + statusz_after)"
    assert ext_mock.LAST_ARGS[0] == 'http://hs-mud:8080/update?arm-away(auto)/away/away'

