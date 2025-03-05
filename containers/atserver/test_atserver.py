#!/usr/bin/python3

import os, pytest, socket, time, warnings
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# TODO: write some real tests
def test_noop():
    pass
