
import context_ci

import os

# We can't just import d-run.py, as it's got an invalid module name...
import kcore.uncommon as UC
DRUN = UC.load_file_as_module('d-run.py', 'drun')


# ---------- helpers

def assert_pair(haystack, needle1, needle2):
    for pos, i in enumerate(haystack):
        if i == needle1:
            if haystack[pos + 1] == needle2: return
    assert False, f'"{needle1}:{needle2}" not found in {haystack}'


# ---------- tests

def test_settings():
    os.environ['DRUN_tz'] = 'America/ZZZ'
    DRUN.parse_args(['--debug', '-l', '-S',
                   '--host_level_settings', 'testdata/host-settings.yaml',
                   '--settings', 'testdata/settings.yaml'])

    assert DRUN.DEBUG
    assert not DRUN.TEST_MODE
    s = DRUN.KS.s

    # Assert settings via flags (that should override values from settings files)
    assert s['tag'] == 'latest'
    assert s.get_bool('shell')

    # Assert settings from container-specific file (that should override host-level file)
    assert s['ip'] == '1.2.3.4'
    assert s['network'] == 'net2'
    assert s['ports'][0][8080] == 8081
    assert s['mount_ro'][0] == 'localvol, /tmp/localvol'
    assert s['mount_rw'][0] == '/tmp/hosttmp, /tmp/hosttmp'

    # Assert settings from host-level settings file
    assert s['repo1'] == 'repo1-val'
    assert s['repo2'] == 'repo2-val'

    # Check defaults taken from the environment
    assert s['tz'] == 'America/ZZZ'

    # Check mode-specific defaults
    assert s['fg'] == '0'
    assert s['log'] == 'none'


def test_generated_command():
    os.environ['DRUN_tz'] = 'America/ZZZ'
    DRUN.parse_args(['--debug', '--name', 'test123', '-l', '-S',
                   '--host_level_settings', 'testdata/host-settings.yaml',
                   '--settings', 'testdata/settings.yaml'])

    cmnd = DRUN.gen_command()
    assert cmnd[0] == '/bin/echo'
    assert cmnd[1] == 'run'
    assert_pair(cmnd, '--name', 'test123')
    assert_pair(cmnd, '--hostname', 'testdata')
    assert_pair(cmnd, '--network', 'net2')
    assert '--log-driver=none' in cmnd
    assert_pair(cmnd, '--user', '0')
    assert '-ti' in cmnd
    assert_pair(cmnd, '--entrypoint', '/bin/bash')
    assert_pair(cmnd, '--mount', 'type=bind,source=/tmp/test123/localvol,destination=/tmp/localvol,readonly')
    assert_pair(cmnd, '--mount', 'type=bind,source=/tmp/hosttmp,destination=/tmp/hosttmp')
    assert_pair(cmnd, '--publish', '0.0.0.0:8080:8081')
    assert_pair(cmnd, '--env', 'TZ=America/ZZZ')
    if os.getuid() == 0: assert_pair(cmnd, '--ip', '1.2.3.4')
    assert 'repo1-val/testdata:latest' in cmnd
