#!/usr/bin/python3

import os, pytest, shutil, sys
import kcore.common as C
import kcore.docker_lib as D

PSWD_ENTRY = 'test:x:9999:9999:test user:/home:/bin/bash'

# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test():
    container_data = D.find_or_start_container_env()

    # copy over test login key
    src = os.path.join(container_data.settings_dir, 'ssh-test-key.pub')
    dest = os.path.join(container_data.vol_dir, '_rw_dv_sshdock_authkeys/test')
    shutil.copyfile(src, dest)
    if os.getuid() == 0:
        os.chmod(dest, 0o644)
        os.chown(dest, 200000, 200000)  # TODO: Ken/jack specific ownership

    # create password entry
    dest = os.path.join(container_data.vol_dir, '_rw_dv_sshdock_passwd')
    with open(dest, 'a') as f:
        f.write(PSWD_ENTRY + '\n')

    return container_data


# ---------- tests

def test_sshdock(container_to_test):
    port = 2222 + container_to_test.port_shift
    ssh_key = os.path.join(container_to_test.settings_dir, 'ssh-test-key')

    rslt = C.popen([
        '/usr/bin/ssh', '-v', '-i', ssh_key, '-o', 'StrictHostKeyChecking=no',
        '-p', str(port), 'test@localhost', 'cat /etc/passwd'])
    assert rslt.ok
    assert PSWD_ENTRY in rslt.out
