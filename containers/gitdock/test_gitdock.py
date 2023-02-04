#!/usr/bin/python3

import atexit, os, pytest, shutil, subprocess, tempfile
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- helpers

def cleanup(tmpdir, orig_dir):
    os.chdir(orig_dir)
    shutil.rmtree(tmpdir)


# ---------- tests

def test_gitdock(container_to_test):
    orig_dir = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    atexit.register(cleanup, tmpdir, orig_dir)

    os.chdir(tmpdir)
    subprocess.check_call(
        ['git', 'clone', 'git-ro@%s:git/rc.git' % container_to_test.ip],
        env={ 'GIT_SSH_COMMAND': f'/usr/bin/ssh -i {container_to_test.settings_dir}/git-ro-test-key -o StrictHostKeyChecking=no' })
    D.file_expect('exit with status', 'rc/.profile')

    print('pass')
