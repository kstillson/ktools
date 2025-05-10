#!/usr/bin/python3

import os, pytest, shutil, subprocess, sys, time
import kcore.docker_lib as D


# ---------- fixture for container under test

# TODO: Ken/jack specific path
PREFIX = '/rw/dv/TEST/filewatchdock/tmp2/'

FILE1 = PREFIX + 'file1'         # max age 10
FILE2 = PREFIX + 'file2'         # should not contain "xx"
DIR1 = PREFIX + 'dir1'
DIR2 = PREFIX + 'dir2'

FILE1_1 = DIR1 + '/file1-1'  # should not exist
FILE2_1 = DIR2 + '/file2-1'  # newest in DIR2 must be max 10
FILE2_2 = DIR2 + '/file2-2'


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- helpers

def mkdirs(dirs):
    for dir in dirs:
        if os.path.exists(dir): shutil.rmtree(dir)
        os.mkdir(dir)


def setfile(fname, contents):
    with open(fname, 'w') as f:
        print(contents, file=f)


def touch(fname, delta=0):   # delta in seconds
    print(f'touch {fname} -> {delta}', file=sys.stderr)
    open(fname, 'a').close()
    newtime = int(time.time()) + delta
    os.utime(fname, (newtime, newtime))


# ---------- tests

def test_filewatch(container_to_test):
    # prep test files
    mkdirs([DIR1, DIR2])
    touch(FILE2_1)
    touch(FILE1)
    touch(FILE2)

    testhost = container_to_test.ip
    testport = 8080
    
    # First check that everything is ok.
    D.web_expect('all ok', testhost, '/', testport)

    # check if file1 aging process
    touch(FILE1, -5)
    D.web_expect('all ok', testhost, '/', testport)
    touch(FILE1, -15)
    D.web_expect('ERROR', testhost, '/', testport)
    os.unlink(FILE1)
    D.web_expect('ERROR', testhost, '/', testport)
    touch(FILE1)
    D.web_expect('all ok', testhost, '/', testport)

    # test contents check for file2
    setfile(FILE2, 'xy')
    D.web_expect('all ok', testhost, '/', testport)
    setfile(FILE2, 'ho-there xx 123')
    D.web_expect('ERROR', testhost, '/', testport)
    setfile(FILE2, '')
    D.web_expect('all ok', testhost, '/', testport)

    # create unexpected file in dir1
    touch(FILE1_1)
    D.web_expect('ERROR', testhost, '/', testport)
    os.unlink(FILE1_1)
    D.web_expect('all ok', testhost, '/', testport)

    # test dir2 newest check
    touch(FILE2_1, -15)
    D.web_expect('ERROR', testhost, '/', testport)
    touch(FILE2_2)
    D.web_expect('all ok', testhost, '/', testport)
