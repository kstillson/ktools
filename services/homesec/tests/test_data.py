
import context_homesec     # fix path to includes work as expected in tests

import kcore.common as common

import pytest

import data as D


# ---------- testing infrastructure

@pytest.fixture(scope='module')
def setup_test():
    # Log to stdout (for easier test debugging)
    common.init_log('debug log', '-', filter_level_logfile=common.DEBUG)


# ---------- tests

def test_post_init(setup_test):
    tl = D.TriggerLookup('a.*', 'zone', 'part')
    assert tl.re.match('abc')
    assert not tl.re.match('def')


# TODO: requires a prep stage to populate an example private.d file.
def test_user_secrets(setup_test):
    assert len(D.USER_SECRETS) > 0


def test_touch_data_getter(setup_test):
    D.TOUCH_DATA.filename = 'testdata/test-touch.data'
    D.TOUCH_DATA.cache = None
    td = D.get_touch_data()
    assert td[0].trigger == 'ken'
    assert td[1].last_update == 456


def test_saved_list_setter(tmp_path):
    filename = tmp_path / "touchdata"
    D.TOUCH_DATA.filename = filename
    D.TOUCH_DATA.cache = None
    with D.saved_list(D.TOUCH_DATA) as tdata:
        assert len(tdata) == 0
        tdata.append(D.TouchData('user11', 11, 'home'))
        tdata.append(D.TouchData('user22', 22, 'away'))
    with D.saved_list(D.TOUCH_DATA) as tdata:
        assert len(tdata) == 2
        tdata.pop(0)
        tdata.append(D.TouchData('user33', 33, 'away'))
    with D.saved_list(D.TOUCH_DATA) as tdata:
        assert len(tdata) == 2
        assert tdata[0].trigger == 'user22'
        assert tdata[1].last_update == 33
