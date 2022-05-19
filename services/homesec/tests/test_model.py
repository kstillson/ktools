
import context_homesec     # fix path to includes work as expected in tests

import os, shutil, tempfile

import pytest
import model as M


@pytest.fixture(scope='module')
def populate_data():
    tmpdir = tempfile.mkdtemp()

    psf = M.data.PARTITION_STATE_FILENAME = os.path.join(tmpdir, 'test-partition-state.data')
    with open(psf, 'w') as f:
        f.write("PartitionState(partition='default', state='arm-auto', last_update=123)\n")
        f.write("PartitionState(partition='safe', state='arm-away', last_update=345)\n")

    tdf = M.data.TOUCH_DATA_FILENAME = os.path.join(tmpdir, 'test-touch.data')
    with open(tdf, 'w') as f:
        f.write("TouchData(trigger='user1', last_update=123, value='home')\n")
        f.write("TouchData(trigger='user2', last_update=456, value='away')\n")
        # These trigger names match some in data.TRIGGER_LOOKUPS
        f.write("TouchData(trigger='back_door', last_update=654)\n")
        f.write("TouchData(trigger='front_door', last_update=321)\n")
        f.write("TouchData(trigger='other', last_update=999)\n")

    yield tmpdir
    shutil.rmtree(tmpdir)


# ---------- tests

def test_get_friendly_touches(populate_data):
    ft = M.get_friendly_touches()

    # Should have 2 triggers that match friendly names from TRIGGER_LOOKUPS.
    assert len(ft) == 2

    # They should be sorted by last udpate, and both be 'tardy'
    assert ft[0].trigger == 'front_door'
    assert ft[0].friendly_name == 'front door'
    assert ft[0].tardy
    assert ft[1].trigger == 'back_door'


def test_get_state_rules(populate_data):
    rules = M.get_state_rules('default', 'enter', 'alarm')
    assert len(rules) == 3
    assert rules[0][0] == 'announce'


def test_other_touch_tests(populate_data):
    assert M.get_touch_status_for('user1') == 'home'
    assert M.get_touch_status_for('user2') == 'away'
    assert M.get_touch_status_for('invalid') is None

    touches = M.get_touches(search=['user1', 'user2'])
    assert touches[0].last_update == 123
    assert touches[1].last_update == 456

    assert M.last_trigger_touch('front_door') == 321


def test_lookup_trigger(populate_data):
    assert M.lookup_trigger('front_door').friendly_name == 'front door'
    assert M.lookup_trigger('panic123_button').zone == 'panic'
    assert M.lookup_trigger('invalid-trigger') is None


def test_lookup_trigger_rules(populate_data):
    # lookup_trigger_rule(state, partition, zone, trigger)
    assert M.lookup_trigger_rule('panic', 'default', 'inside', 'arm-home')[0] == 'announce'
    assert M.lookup_trigger_rule('panic', 'default', None, 'disarm')[1] == 'disarmed'
    assert M.lookup_trigger_rule('test-mode', 'default', 'panic', 'panic1')[0] == 'announce'
    assert M.lookup_trigger_rule('arm-home', 'default', 'inside', 'door')[0] == 'pass'
    assert M.lookup_trigger_rule('arm-home', 'default', 'outside', 'door')[0] == 'announce'
    assert M.lookup_trigger_rule('arm-away', 'default', 'inside', 'door')[1].startswith('alarm-triggered')
    assert M.lookup_trigger_rule('arm-away', 'default', 'outside', 'door')[0] == 'pass'
    assert M.lookup_trigger_rule('disarmed', 'default', 'inside', 'door')[0] == 'pass'

