#!/usr/bin/python3

# - You'll need a files/root/.config/rclone/private.d/rclone.conf
#   whose decryption key (if used) can be obtained by files/etc/auth, and
#   where the name of the repository matches between the rclone config and
#   the "test)" section of files/etc/init.

import os, pytest, sys, time
import kcore.docker_lib as D


# ---------- control constants

# TODO: Ken/jack specific paths
TEST_FILE_OUT = '/rw/mnt/rsnap/echo-back/test-out'
TEST_FILE_COPYBACK = '/rw/mnt/rsnap/echo-back/test-in/test-out'


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def setup_session():
    # Need cookie generation to happen before launching contianer, as container runs really quick.
    cookie = D.gen_random_cookie()
    with open(TEST_FILE_OUT, 'w') as f: f.write(cookie)
    os.chmod(TEST_FILE_OUT, 0o644)    # TODO: Ken/jack specific permissions
    os.chown(TEST_FILE_OUT, 200000, 200000)
    
    container_to_test = D.find_or_start_container_env(settings='settings-test.yaml')
    return cookie, container_to_test


# ---------- helpers

def comp_file(filename, expected_contents):
    if not os.path.isfile(filename): return False
    with open(filename) as f: contents = f.read()
    match = expected_contents == contents
    print(f'comp_file: {expected_contents=} {contents=} {match=}')
    return match


def skip_if():
    return D.not_required_host('jack') or D.check_env_for_prod_mode()

# ---------- tests

@pytest.mark.skipif(skip_if(), reason='test contains host-specific configuration requirements (wasabi creds) and only works in test mode.')
def test_rclonedock(setup_session):
    cookie, container_to_test = setup_session
    for i in range(5):
        if comp_file(TEST_FILE_COPYBACK, cookie): return
        time.sleep(2)
    assert False, 'unable to find matching contents :-('
