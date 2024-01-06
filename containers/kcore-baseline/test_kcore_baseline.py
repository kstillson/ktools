#!/usr/bin/python3

import os, pytest, subprocess, sys
import kcore.docker_lib as D
import ktools.ktools_settings as KS


# ---------- control constants

s = KS.init(test_mode=True)
DOCKER_BIN = s.get('docker_exec', os.environ.get('DOCKER_EXEC', 'docker'))


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_image_prep(container_to_test):
    '''Check that our files/prep got put into place.'''
    D.container_file_expect('APK_CLEANUP=1', container_to_test.name, '/prep')


def test_cow(container_to_test):
    '''Check a file created in the container is visible in the expected cow directory.'''
    cookie = D.gen_random_cookie()
    subprocess.check_call(
        [DOCKER_BIN, 'exec', '-u', '0', container_to_test.name,
         '/bin/bash', '-c', 'echo "%s" > /root/cookie' % cookie])
    D.file_expect(cookie, os.path.join(container_to_test.cow, 'root/cookie'))
    

def test_kcore_works_inside_container(container_to_test):
    D.popen_inside_expect(
        container_to_test.name,
        ['python3', '-c', 'import kcore.common; print("ok")'], 'ok', expect_returncode=0)
    

    # ---- Make sure bash-history is being recorded in cow dir.
    # TODO: can't find a way to run this in an automated way that looks sufficiently
    # like it's interactive so that bash records it.  Tried various combinations of
    # passing -ti to docker and -il to bash, no joy.  Disabling for now.
    # On the plus side, actual interactive sessions do seem to get logged.
    ## D.file_expect(cookie, cow + '/root/.bash_history')
