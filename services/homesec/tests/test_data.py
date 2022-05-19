
import context_homesec     # fix path to includes work as expected in tests

import data as D


def test_post_init():
    tl = D.TriggerLookup('a.*', 'zone', 'part')
    assert tl.re.match('abc')
    assert not tl.re.match('def')


# TODO: requires a prep stage to populate an example private.d file.
def test_user_secrets():
    assert len(D.USER_SECRETS) > 0


def test_touch_data_getter():
    D.TOUCH_DATA_FILENAME = 'testdata/touch.data'
    td = D.get_touch_data()
    assert td[0].trigger == 'user1'
    assert td[1].last_update == 456


def test_saved_list_setter(tmp_path):
    filename = tmp_path / "touchdata"
    with D.saved_list(filename, D.TouchData) as tdata:
        assert len(tdata) == 0
        tdata.append(D.TouchData('user11', 11, 'home'))
        tdata.append(D.TouchData('user22', 22, 'away'))
    with D.saved_list(filename, D.TouchData) as tdata:
        assert len(tdata) == 2
        tdata.pop(0)
        tdata.append(D.TouchData('user33', 33, 'away'))
    with D.saved_list(filename, D.TouchData) as tdata:
        assert len(tdata) == 2
        assert tdata[0].trigger == 'user22'
        assert tdata[1].last_update == 33
