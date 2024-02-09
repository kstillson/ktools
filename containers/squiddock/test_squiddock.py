#!/usr/bin/python3

import os, pytest, sys, time
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_squiddock(container_to_test):
    time.sleep(3)
    port = 3128 + container_to_test.port_shift
    D.web_expect('little place', 'kenstillson.com', '/', proxy_host=f'localhost:{port}')
    D.file_expect('http://kenstillson.com/', container_to_test.vol_dir + '/var_log_squid/access.log')
