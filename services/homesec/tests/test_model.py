
import context_homesec     # fix path to includes work as expected in tests

import os, shutil, tempfile

import kcore.common as common

import pytest
import model as M


@pytest.fixture(scope='module')
def setup_test():
    # Log to stdout (for easier test debugging)
    common.init_log('debug log', '-', filter_level_logfile=common.DEBUG)

    tmpdir = tempfile.mkdtemp()
    dest = tmpdir + '/test-partition-state.data'
    shutil.copyfile('testdata/test-partition-state.data', dest)
    M.data.PARTITION_STATE.filename = dest
    M.data.PARTITION_STATE.cache = None

    dest = tmpdir + '/test-touch.data'
    shutil.copyfile('testdata/test-touch.data', dest)
    M.data.TOUCH_DATA.filename = dest
    M.data.TOUCH_DATA.cache = None

    yield tmpdir
    shutil.rmtree(tmpdir)


# ---------- tests

def test_get_friendly_touches(setup_test):
    ft = M.get_friendly_touches()

    # Should have 2 triggers that match friendly names from TRIGGER_LOOKUPS.
    assert len(ft) == 2

    # They should be sorted by last udpate, and both be 'tardy'
    assert ft[0].trigger == 'front_door'
    assert ft[0].friendly_name == 'front door'
    assert ft[0].tardy
    assert ft[1].trigger == 'back_door'


def test_get_state_rules(setup_test):
    rules = M.get_state_rules('default', 'enter', 'alarm')
    assert len(rules) == 3
    assert rules[0][0] == 'announce'


def test_other_touch_tests(setup_test):
    assert M.get_touch_status_for('ken') == 'home'
    assert M.get_touch_status_for('dad') == 'away'
    assert M.get_touch_status_for('invalid') is None

    touches = M.get_touches()
    assert touches[0].last_update == 123
    assert touches[1].last_update == 456

    assert M.last_trigger_touch('front_door') == 321


def test_lookup_trigger(setup_test):
    assert M.lookup_trigger('front_door').friendly_name == 'front door'
    assert M.lookup_trigger('panic123_button').zone == 'panic'
    assert M.lookup_trigger('invalid-trigger') is None


def test_lookup_trigger_rules(setup_test):
    # lookup_trigger_rule(state, partition, zone, trigger)
    assert M.lookup_trigger_rule('panic', 'default', 'inside', 'arm-home')[0] == 'announce'
    assert M.lookup_trigger_rule('panic', 'default', None, 'disarm')[1] == 'disarmed'
    assert M.lookup_trigger_rule('test-mode', 'default', 'panic', 'panic1')[0] == 'announce'
    assert M.lookup_trigger_rule('arm-home', 'default', 'inside', 'door')[0] == 'pass'
    assert M.lookup_trigger_rule('arm-home', 'default', 'outside', 'door')[0] == 'announce'
    assert M.lookup_trigger_rule('arm-away', 'default', 'inside', 'door')[1].startswith('alarm-triggered')
    assert M.lookup_trigger_rule('arm-away', 'default', 'outside', 'door')[0] == 'pass'
    assert M.lookup_trigger_rule('disarmed', 'default', 'inside', 'door')[0] == 'pass'

