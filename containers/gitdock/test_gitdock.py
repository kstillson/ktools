#!/usr/bin/python3

# TODO: copy over test key creation from ../sshdock/test_sshdock.py

import atexit, os, pytest, shutil, subprocess, tempfile
import kcore.common as C
import kcore.docker_lib as D

# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- helpers

def cleanup(tmpdir, orig_dir):
    os.chdir(orig_dir)
    shutil.rmtree(tmpdir)


# ---------- tests

@pytest.mark.skipif(D.check_env_for_prod_mode(), reason='creds only work in test mode')
def test_gitdock(container_to_test):
    orig_dir = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    atexit.register(cleanup, tmpdir, orig_dir)

    port = 2223 + container_to_test.port_shift
    os.chdir(tmpdir)
    cmd = ['git', 'clone', 'git-ro@localhost:git']
    env = { 'GIT_SSH_COMMAND': f'/usr/bin/ssh -i {container_to_test.settings_dir}/testdata/git-ro-test-key -p {port} -v -o StrictHostKeyChecking=no' }
    rslt = C.popen(cmd, env=env, timeout=5)
    print(f'{cmd=} {env=} -> {rslt.out=}')

    D.file_expect('hithere', 'git/file.txt')

    print('pass')
