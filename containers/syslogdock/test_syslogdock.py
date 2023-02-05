#!/usr/bin/python3

import pytest, subprocess, time
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_syslogdock(container_to_test):
    port = 1514 + container_to_test.port_shift
    cookie = D.gen_random_cookie()

    subprocess.check_call(['/usr/bin/logger', '-T', '-n', 'localhost', '-p', 'local1.info', '-P', str(port), cookie])
    time.sleep(1)  # Give syslog a chance to process.

    D.container_file_expect(cookie, container_to_test.name, '/var/log/queue')

