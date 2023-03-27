
import argparse, os, pytest, sys

import context_kcore     # fix path to includes work as expected in tests
import kcore.settings as S

import kcore.uncommon as UC


# ---------- infrastructure

ENV = None
def reset_env():
    global ENV
    if not ENV:
        ENV = dict(os.environ)
    else:
        os.environ.clear()
        os.environ.update(ENV)


# ---------- tests

def test_simple_yaml_only():
    reset_env()
    os.environ['e1'] = 'e1val-env9'

    s = S.Settings('testdata/settings1.yaml')
    assert s.get('a') == 'val-a'
    assert s['c'] == '321'
    assert s['d']['k1'] == 'v1'
    assert s['d']['k2'] == 'v2'
    assert s['l'][0] == 'l1'
    assert s['l'][1] == 'l2'
    assert s['e1'] == 'e1val-env9'
    assert s['f'].startswith('hello')
    assert s['n'] == 123
    assert s['missing'] is None


def test_simple_env_only():
    s = S.Settings(debug=True)
    s.add_setting('e1', default_env_value='e1missing')

    parse_results = s.parse_settings_file('testdata/settings2.env')
    assert s['a'] == 'val-ae'
    assert s['c'] == '321e'
    assert s['e1'] == 'e1missing'
    assert s['f'].startswith('hello')
    assert s['n'] == '124'                  # note conversion to string (because .env file doesn't have types)
    assert parse_results['f'].startswith('file:')


def test_simple_dict_file_only():
    s = S.Settings('testdata/settings3.dict')
    s.get_setting('e1').default_env_value = 'e1missing2'
    assert s['a'] == 'val-ad'
    assert s['c'] == '321d'
    assert s['d']['k1'] == 'v1d'
    assert s['d']['k2'] == 'v2d'
    assert s['l'][0] == 'l1d'
    assert s['l'][1] == 'l2d'
    assert s['e1'] == 'e1missing2'
    assert s['n'] == 125


def test_yaml_plus_environment():
    reset_env()
    os.environ['e1'] = 'e1val-env'
    os.environ['e2'] = 'e2val-env'
    os.environ['q1'] = 'q1val-env'
    os.environ['eo_n'] = 'n-override-env'

    settings = S.Settings('testdata/settings1.yaml', debug=True)
    settings.add_simple_settings(['a', 'c', 'd', 'l', 'e1', 'e2', 'ex', 'f', 'n', 'q1', 'q2', 'q3'])
    # reach in a change some settings' controls...
    settings.tweak_setting('q2', 'default', 'def-q2')
    settings.tweak_all_settings('override_env_name', 'eo_{name}')
    settings.tweak_all_settings('env_name', '')  # change None to '' to trigger default of {name}

    assert settings.get('a') == 'val-a'  # from yaml
    assert settings.get_setting('a').cached_value == 'val-a'  # check value was cached
    assert settings.get_setting('a').how == 'setting a from file testdata/settings1.yaml'
    assert settings['missing'] is None   # Check completely unknown control.

    # Try a few via get_dict()
    s = settings.get_dict()
    assert s['d']['k1'] == 'v1'
    assert s['l'][1] == 'l2'

    # Check that yaml file referening env-vars works.
    assert s['e1'] == 'e1val-env'
    assert s['e2'] == 'e2val-env'
    assert settings.get_setting('e2').how == 'setting e2 from file testdata/settings1.yaml; after arg resolved for: $e2'

    assert s['ex'][0] == 'e1val-env'
    assert s['ex'][1] == 'e2val-env'
    assert settings.get_setting('e2').how == 'setting e2 from file testdata/settings1.yaml; after arg resolved for: $e2'

    assert s['f'].startswith('hello')   # Check that file loading works.
    assert settings.get_setting('f').how == 'setting f from file testdata/settings1.yaml; after arg resolved for: file:testdata/file1'

    assert s['q1'] == 'q1val-env'       # Check that environment default works.
    assert settings.get_setting('q1').how == 'environment variable $q1'
    assert s['q2'] == 'def-q2'          # Check that control-level default works.
    assert settings.get_setting('q2').how == 'default string'
    assert s['q3'] is None              # Check control defined by nothing works.

    assert s['n'] == 'n-override-env'   # Check that environment override works.
    assert settings.get_setting('n').how == 'override environment variable $eo_n'

    # Check that an undefined setting present in the settings file can be retrieved
    # from the settings-file-specific cache and doesn't hurt anything else.
    assert settings._settings_file_value_cache.get('extra') == 'mostly harmless'


def test_env_values_only_when_requested():
    reset_env()
    os.environ['q1'] = 'q1val-x'
    os.environ['eo_q1'] = 'q1val-xx'

    settings = S.Settings(debug=True)  # no env_names are set, no datafile provided.
    settings.add_setting('q1')
    assert settings['q1'] is None

    settings2 = S.Settings(debug=True)
    settings2.add_setting('q1', env_name='q1')
    assert settings2['q1'] == 'q1val-x'

    settings3 = S.Settings(debug=True)
    settings3.add_setting('q1', override_env_name='eo_q1')
    assert settings3['q1'] == 'q1val-xx'

    settings4 = S.Settings(debug=True)
    settings4.add_setting('q1', override_env_name='q1')
    assert settings4['q1'] == 'q1val-x'


def test_including_flags_in_the_mix():
    reset_env()
    settings = S.Settings('testdata/settings2.env', flag_prefix="f_", debug=True)
    settings.add_simple_settings(['a', 'c', 'd', 'l', 'e1', 'e2', 'ex', 'f', 'n', 'q1', 'q2', 'q3'])
    settings.tweak_all_settings('override_env_name', 'eo_{name}')

    ap = argparse.ArgumentParser()
    ap.add_argument('--local', help='flag not associated with the settings system')
    settings.add_flags(ap)

    argv = ['--local=l1val', '--f_d', 'dflag', '--f_n', '999']
    args = ap.parse_args(argv)
    assert args.local == 'l1val'

    # This shouldn't be needed in real code, but the default argparse.parse_args() called
    # from within a testing framework returns junk, so manually set the args to use.
    settings.set_args(args)

    # Check that values not touched by flags still work.
    # also checks conversion of Settings to string (which runs get)
    assert settings.get('c') == '321e'

    # Check that values provided only by the flag pick up their value.
    assert settings['d'] == 'dflag'

    # Check that flag takes priority over the settings file.
    assert settings['n'] == '999'  # note that it's a string now.

    # We didn't provide for a regular environment variable default, so make sure
    # it's successfully deactivated.
    os.environ['q1'] = 'q1val1'
    assert settings['q1'] is None

    # Now let's give it a default value and cause that to be cached.
    settings.get_setting('q1').default = 'q1val-d'
    assert settings['q1'] is 'q1val-d'

    # We did provide for override environment variables, but first lets check
    # that cached values are returned for things we've already checked.
    os.environ['eo_q1'] = 'q1val2'
    assert settings['q1'] is 'q1val-d'  # returns cached non-overriden value

    # Now check that the override works when ignoring caching.
    assert settings.get('q1', ignore_cache=True) == 'q1val2'


def test_multiple_settings_files():
    settings = S.Settings('testdata/settings1.yaml', debug=True)
    settings.add_simple_settings(['a', 'd'])
    assert settings['a'] == 'val-a'
    assert settings['d']['k1'] == 'v1'

    # Note that we are not asserting ignore_cache=True; parse_settings_file()
    # should invalidate the cache automatically.

    settings.parse_settings_file('testdata/settings2.env')
    assert settings['a'] == 'val-ae'       # changed
    assert settings['d']['k1'] == 'v1'     # unchanged (not set in the 2nd file)


def test_list_of_Settings():
    settings = S.Settings('testdata/settings3.dict', debug=True)
    settings.add_Settings([
        S.Setting('z1', setting_name='a',       default='d1'),
        S.Setting('z2', setting_name='missing', default='d2'),
        S.Setting('z3', setting_name='n',       default='d3', flag_type=int),
    ])

    assert settings['z1'] == 'val-ad'
    assert settings['z2'] == 'd2'
    assert settings.get('z3') == 125

def test_default_callable():
    settings = S.Settings(debug=True)
    toggle = True
    settings.add_setting('s', disable_cache=True, default=lambda: 'is-true' if toggle else 'is-false')
    assert settings['s'] == 'is-true'
    toggle = False
    assert settings['s'] == 'is-false'

def test_env_sep():
    reset_env()
    os.environ['s'] = 'a;b'
    settings = S.Settings(debug=True)
    settings.add_setting('s', env_name='s')
    assert settings['s'] == ['a', 'b']

    os.environ['s2'] = 'a, b'
    settings = S.Settings(env_list_sep=', ', debug=True)
    settings.add_setting('s2', env_name='s2')
    assert settings['s2'] == ['a', 'b']


def test_chained_include_directives():
    settings = S.Settings('testdata/settings4.env', debug=True)
    assert settings['a'] == '1'    # from settings4
    assert settings['b'] == '2'    # from settings4
    assert settings['c'] == 5      # from settings5
    assert settings['d'] == 6      # from settings6

def test_settings_file_glob_and_include_dir():
    settings = S.Settings(['testdata/settings2.env', 'testdata/settings7.e*'], debug=True)
    assert settings['a'] == '9'    # from settings7
    assert settings['b'] is None
    assert settings['c'] == 'cval' # from data.d/file1.yaml
    assert settings['d'] == 'dval' # from data.d/file2.env
    assert settings['f'].startswith('hello')  # from settings2.env

def test_typed_settings():
    reset_env()
    settings = S.Settings('testdata/settings2.env', debug=True)

    # bool
    os.environ['e1e'] = '1'
    assert settings.get_bool('e1', True)
    os.environ['e1e'] = '0'
    assert not settings.get_bool('e1', True)
    os.environ['e1e'] = 'True'
    assert settings.get_bool('e1', True)
    os.environ['e1e'] = 'x'
    assert not settings.get_bool('e1', True)

    # int
    os.environ['e1e'] = '1'
    assert settings.get_int('e1', None, True) == 1
    os.environ['e1e'] = '0'
    assert settings.get_int('e1', None, True) == 0
    os.environ['e1e'] = 'x'
    assert settings.get_int('e1', None, True) is None
    assert settings.get_int('e1', -1, True) == -1


def test_cli():
    reset_env()
    os.environ['e1e'] = 'e1e-e'
    os.environ['e2e'] = 'e2e-e'

    argv = ['--settings_filename', 'testdata/settings2.env', 'a']
    with UC.Capture() as cap:
        ret = S.main(argv)
        assert ret == 0
        assert cap.out == 'a=val-ae'
        assert cap.err == ''

    argv = ['--settings_filename', 'testdata/settings2.env', '--quotes', 'a', 'c', 'e2']
    with UC.Capture() as cap:
        ret = S.main(argv)
        assert ret == 0
        assert cap.out == 'a="val-ae"\nc="321e"\ne2="e2e-e"'
        assert cap.err == ''

    argv = ['--settings_filename', 'testdata/settings2.env', '--all']
    with UC.Capture() as cap:
        ret = S.main(argv)
        assert ret == 0
        assert 'f=hello world' in cap.out
        assert '=None' not in cap.out

    argv = ['--bare', '--settings_filename', 'testdata/settings2.env', 'a']
    with UC.Capture() as cap:
        ret = S.main(argv)
        assert ret == 0
        assert cap.out == 'val-ae'
        assert cap.err == ''
