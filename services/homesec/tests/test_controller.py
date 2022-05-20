
import context_homesec     # fix path to includes work as expected in tests

import datetime, os, shutil, tempfile, time

import kcore.common as common

import pytest
import controller as C


# Replace ext module with its testing mock.
import ext_mock
C.ext = ext_mock

# ---------- testing infrastructure

@pytest.fixture(scope='module')
def setup_test():
    # Log to stdout (for easier test debugging)
    common.init_log('debug log', '-')

    # Test-friendly timing changes.
    C.model.data.CONSTANTS['ALARM_TRIGGERED_DELAY'] = 1
    C.model.data.CONSTANTS['ALARM_DURATION'] = 2

    # Copy over test data
    tmpdir = tempfile.mkdtemp()
    dest = tmpdir + '/test-partition-state.data'
    shutil.copyfile('testdata/test-partition-state.data', dest)
    C.model.data.PARTITION_STATE_FILENAME = dest

    dest = tmpdir + '/test-touch.data'
    shutil.copyfile('testdata/test-touch.data', dest)
    C.model.data.TOUCH_DATA_FILENAME = dest

    yield tmpdir
    shutil.rmtree(tmpdir)


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
        'force_zone': None,
        'lookup_zone': 'default',
        'params': '%u',
        'partition': 'default',
        'partition_start_state': 'arm-auto',
        'speak': 'homesec armed',
        'state': 'arm-home',
        'trigger': 'touch-away',
        'trigger_friendly': None,
        'zone': 'default',
        'user': 'ken', }
    assert C.get_statusz_state() == 'arm-away(auto)/away/away'
    if datetime.datetime.now().hour >= 18:
        assert ext_mock.LAST == "ext.control('away', 'go')"
    else:
        assert ext_mock.LAST == "ext.announce('homesec armed')"

    # An outside trigger has no effect.
    status, tracking = C.run_trigger(fake_request_dict, 'door', 'outside')
    assert status == 'ok'
    assert tracking['action'] == 'pass'
    assert C.get_statusz_state() == 'arm-away(auto)/away/away'

    # A duplicate trigger is squelched.
    status, tracking = C.run_trigger(fake_request_dict, 'door', 'outside')
    assert status == 'squelched'

    # An default trigger raises the alarm.
    status, tracking = C.run_trigger(fake_request_dict, 'some-other-door')
    assert status == 'ok'
    assert tracking['action'] == 'state-delay-trigger'
    assert C.get_statusz_state() == 'alarm-triggered/away/away'
    assert ext_mock.LAST == 'ext.push_notification(msg, level)'
    assert 'alarm triggered' in ext_mock.LAST_ARGS[0]

    time.sleep(0.7)
    if 'triggered' in C.get_statusz_state(): time.sleep(0.7)
    assert C.get_statusz_state() == 'alarm/away/away'
    assert ext_mock.LAST == "C.log('httpget action returned: %s' % ext.read_web(params))"
    assert '/panic' in ext_mock.LAST_ARGS[0]

    time.sleep(1.5)
    if 'alarm/' in C.get_statusz_state(): time.sleep(0.8)
    if 'alarm/' in C.get_statusz_state(): time.sleep(0.8)
    assert C.get_statusz_state() == 'arm-away(auto)/away/away'
    assert ext_mock.LAST == 'ext.push_notification(msg, level)'
    assert 'automatic arming mode' in ext_mock.LAST_ARGS[0]

