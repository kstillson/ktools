#!/usr/bin/python3

import os, pytest, sys

import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_dnsdock_default_config(container_to_test):
    prod_mode = os.environ.get('KTOOLS_DRUN_TEST_PROD') == '1'
    port = str(53 + container_to_test.port_shift)
    invalid_random_port = '23871'
    D.popen_expect(['host', '-p', port, 'jack', 'localhost'], 'has address 192.168.1.2')
    D.popen_expect(['host', '-p', port, 'jack2', 'localhost'], 'NXDOMAIN')
    D.popen_expect(['host', '-p', invalid_random_port, 'jack', 'localhost'], 'refused')

