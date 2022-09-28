
import context_homesec     # fix path to includes work as expected in tests

import kcore.common as common
import kcore.persister as P

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


def test_touch_data_getter(setup_test):
    D.TOUCH_DATA.filename = 'tests/test-touch.data'
    td = list(D.TOUCH_DATA.get_data().values())
    assert td[0].trigger == 'ken'
    assert td[1].last_update == 456


def test_saved_list_setter(setup_test, tmp_path):
    filename = tmp_path / "touchdata"
    test_data = P.DictOfDataclasses(filename, D.TouchData)
    with test_data.get_rw() as tdata:
        assert len(tdata) == 0
        tdata['user11'] = D.TouchData('user11', 11, 'home')
        tdata['user22'] = D.TouchData('user22', 22, 'away')
    with test_data.get_rw() as tdata:
        assert len(tdata) == 2
        tdata.pop('user11')
        tdata['user33'] = D.TouchData('user33', 33, 'away')
    tdata = list(test_data.get_data().values())
    assert len(tdata) == 2
    assert tdata[0].trigger == 'user22'
    assert tdata[1].last_update == 33
