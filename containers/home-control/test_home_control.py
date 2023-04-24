#!/usr/bin/python3

import os, pytest, sys
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_home_control(container_to_test):
    port = 3333 + container_to_test.port_shift
    D.web_expect('ok', 'localhost', '/control/test-device/test-command', port=port)
    D.web_expect('test-command', 'localhost', '/varz?TEST-test-device', port=port)
