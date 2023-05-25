#!/usr/bin/python3

import os, pytest, sys
import kcore.docker_lib as D


# ---------- fixture for container under test

LOCALHOST = 'localhost'
PORT = D.pick_test_port()

@pytest.fixture(scope='session')
def init():
    p = D.init_system_under_test(['./home_control_service', '--debug', '--logfile=-', '--port', str(PORT)])
    yield p
    p.kill()


# ---------- tests

def test_home_control(init):
    D.web_expect('ok', LOCALHOST, '/control/test-device/test-command', port=PORT)
    D.web_expect('test-command', LOCALHOST, '/varz?TEST-test-device', port=PORT)
