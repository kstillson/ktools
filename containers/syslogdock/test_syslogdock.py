#!/usr/bin/python3

import pytest, subprocess, sys, time
import kcore.common as C
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_syslogdock(container_to_test):
    server = container_to_test.ip if D.check_env_for_prod_mode() else 'localhost'
    port = 1514 + container_to_test.port_shift
    cookie = D.gen_random_cookie()

    cmd = ['/usr/bin/logger', '-T', '-n', server, '-p', 'local1.info', '-P', str(port), cookie]
    rslt = C.popen(cmd)
    if not rslt.ok: print(f'ERROR test cmd failed: {cmd=} -> {rslt=}', file=sys.stderr)
    time.sleep(2)  # Give syslog a chance to process.

    D.container_file_expect(cookie, container_to_test.name, '/var/log/queue')
