
import context_homesec     # fix path to includes work as expected in tests

import os, shutil, sys, tempfile, time

import kcore.common as common

import pytest
import controller as C

# ---------- testing infrastructure

# Replace ext module with its testing mock.
import ext_mock
C.ext = ext_mock

# Test-friendly timing changes.
C.model.data.CONSTANTS['ALARM_TRIGGERED_DELAY'] = 1
C.model.data.CONSTANTS['ALARM_DURATION'] = 2


@pytest.fixture(scope='module')
def populate_data():
    common.init_log('debug log', '-')
    
    tmpdir = tempfile.mkdtemp()

    psf = C.model.data.PARTITION_STATE_FILENAME = os.path.join(tmpdir, 'test-partition-state.data')
    with open(psf, 'w') as f:
        f.write("PartitionState(partition='default', state='arm-auto', last_update=123)\n")
        f.write("PartitionState(partition='safe', state='arm-away', last_update=345)\n")

    tdf = C.model.data.TOUCH_DATA_FILENAME = os.path.join(tmpdir, 'test-touch.data')
    with open(tdf, 'w') as f:
        f.write("TouchData(trigger='ken', last_update=123, value='home')\n")
        f.write("TouchData(trigger='dad', last_update=456, value='away')\n")
        # These trigger names match some in data.TRIGGER_LOOKUPS
        f.write("TouchData(trigger='back_door', last_update=654)\n")
        f.write("TouchData(trigger='front_door', last_update=321)\n")
        f.write("TouchData(trigger='other', last_update=999)\n")

    yield tmpdir
    shutil.rmtree(tmpdir)


# ---------- tests

def test_typical_sequence(populate_data):
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
    assert ext_mock.LAST.method == 'announce'
    assert ext_mock.LAST.args == ('homesec armed',)

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
    assert ext_mock.LAST.method == 'push_notification'
    assert 'triggered' in ext_mock.LAST.args[0]
    
    time.sleep(0.7)
    if 'triggered' in C.get_statusz_state(): time.sleep(0.7)
    assert C.get_statusz_state() == 'alarm/away/away'
    assert ext_mock.LAST.method == 'read_web'
    assert 'panic' in ext_mock.LAST.args[0]

    time.sleep(1.5)
    if 'alarm/' in C.get_statusz_state(): time.sleep(0.8)
    if 'alarm/' in C.get_statusz_state(): time.sleep(0.8)
    assert C.get_statusz_state() == 'arm-away(auto)/away/away'
    assert ext_mock.LAST.method == 'push_notification'
    assert 'automatic arming mode' in ext_mock.LAST.args[0]
