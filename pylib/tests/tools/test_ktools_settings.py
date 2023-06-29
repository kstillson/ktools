
import os

import context_tools     # fix path to includes work as expected in tests
import kcore.uncommon as UC

import ktools_settings as KS


def test_no_init():
    assert KS.get('fg') == '0'


def test_empty_init():
    KS.init()
    assert KS.get('fg') == '0'
    assert len(KS.get_dict()) > 10


def test_simple_init():
    s = KS.init(['pylib runtime', 'autostart'], 'testdata/ktools_settings1.yaml',
                global_settings_filename=None, debug=True)
    d = s.get_dict()
    assert len(d) > 2
    assert len(d) < 10
    assert d['autostart'] == 99
    assert d['extra'] == 123
    assert 'keymaster_host' in d
    assert not 'simple' in d

    # Check env_name
    os.environ['autostart'] = '456'  # yaml file overrides env_name
    assert d['autostart'] == 99

    assert s.get('keymaster_host') is None  # not defined in yaml file
    os.environ['KT_keymaster_host'] = 'qqq'
    assert s.get('keymaster_host', ignore_cache=True) == 'qqq'  # env_name acts as fallback

    # Check override_env_name
    os.environ['KTO_autostart'] = 'x1'
    assert s.get('autostart', ignore_cache=True) == 'x1'

    os.environ['KTO_extra'] = 'x2'                    # No effect because not defined in ktools_settings, and
    assert s.get('extra', ignore_cache=True) == 123   # thus no registered override_env_name.


def test_cli():
    argv = ['--bare', '--settings', 'testdata/ktools_settings1.yaml', '--host_settings', '', 'extra']
    with UC.Capture() as cap:
        ret = KS.main(argv)
        assert ret == 0
        assert cap.out == '123'
        assert cap.err == ''
