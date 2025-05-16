#!/usr/bin/python3

import os, pytest, sys, time
import kcore.docker_lib as D


# ---------- fixture for container under test

PORT = 8080

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_home_control(container_to_test):
    print('waiting for startup...', file=sys.stderr)
    time.sleep(4)
    D.web_expect('ok', container_to_test.ip, '/control/test-device/test-command', port=PORT)
    D.web_expect('test-command', container_to_test.ip, '/varz?TEST-test-device', port=PORT)
