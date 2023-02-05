#!/usr/bin/python3

import os, pytest, sys
import kcore.docker_lib as D


# TODO: Ken/jack specific path
TEST_FILE = '/rw/dv/TMP/rsnapdock/_rw_mnt_rsnap/daily.0/jack/etc/shadow'


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

@pytest.mark.skipif(D.not_required_host('jack'), reason='test contains host-specific configuration requirements')
def test_rsnapdock(container_to_test):
    # Wait for test file to show up in target dir.
    for i in range(10):
        if os.path.exists(TEST_FILE) and os.path.getsize(TEST_FILE) > 0: break
        time.sleep(2)

    D.file_expect('root:!:', TEST_FILE)
