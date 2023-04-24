#!/usr/bin/python3

import os, pytest, sys
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- helpers

def query_cmd(name, container_to_test):
    cmd = ['host']
    if os.getuid() == 0:
        server = container_to_test.ip
    else:
        server = 'localhost'
        cmd += ['-p', str(53 + container_to_test.port_shift)]
    cmd += [name, server]
    return cmd


# ---------- tests

def test_dnsdock_default_config(container_to_test):
    D.popen_expect(query_cmd('jack',  container_to_test), 'has address 192.168.1.2')
    D.popen_expect(query_cmd('jackX', container_to_test), 'NXDOMAIN')
