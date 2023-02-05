#!/usr/bin/python3

import os, pytest, sys
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_squiddock(container_to_test):
    port = 3128 + container_to_test.port_shift
    D.web_expect('little place', 'www.kenstillson.com', '/', proxy_host=f'localhost:{port}')

    prefix = container_to_test.vol_dir + ('/' if container_to_test.port_shift == 0 else '/_rw_dv_squiddock_')
    D.file_expect('http://www.kenstillson.com/', prefix + 'var_log_squid/access.log')
