#!/usr/bin/python3

import os, pytest, shutil, sys
import kcore.common as C
import kcore.docker_lib as D

PSWD_ENTRY = 'test:x:9999:9999:test user:/home:/bin/bash'

# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test():
    return D.find_or_start_container_env()


# ---------- tests

@pytest.mark.skipif(D.check_env_for_prod_mode(), reason='test requires test-vol specific creds/config.')
def test_sshdock(container_to_test):
    port = 2222 + container_to_test.port_shift
    ssh_key = os.path.join(container_to_test.settings_dir, 'testdata/ssh-test-key')

    rslt = C.popen([
        '/usr/bin/ssh', '-v', '-i', ssh_key, '-o', 'StrictHostKeyChecking=no',
        '-p', str(port), 'test@localhost', 'cat /etc/passwd'])
    assert rslt.ok
    assert PSWD_ENTRY in rslt.out
