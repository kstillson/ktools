#!/usr/bin/python3

import os, pytest, sys
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_homesecdock(container_to_test):
    port = 1111 + container_to_test.port_shift
    server = container_to_test.ip if D.check_env_for_prod_mode() else 'localhost'
    D.web_expect('ok', server, '/healthz', port=port)
