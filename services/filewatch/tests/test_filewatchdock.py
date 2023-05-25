#!/usr/bin/python3

import os, pytest, shutil, subprocess, sys, time
import kcore.docker_lib as D


# ---------- fixture for container under test

FILE1 = '/tmp/file1'         # max age 10
FILE2 = '/tmp/file2'         # should not contain "xx"
DIR1 = '/tmp/dir1'
DIR2 = '/tmp/dir2'
FILE1_1 = DIR1 + '/file1-1'  # should not exist
FILE2_1 = DIR2 + '/file2-1'  # newest in DIR2 must be max 10
FILE2_2 = DIR2 + '/file2-2'

LOCALHOST = 'localhost'
PORT = D.pick_test_port()


@pytest.fixture(scope='session')
def init():
    # prep test files
    mkdirs([DIR1, DIR2])
    touch(FILE2_1)
    touch(FILE1)
    touch(FILE2)

    # launch object under test
    cfg = './filewatch_config_test'
    if not os.path.isfile(cfg): cfg = 'tests/filewatch_config_test'
    p = D.init_system_under_test(['./filewatch', '--config', cfg, '--port', str(PORT)])
    yield p
    print('returned from yield, killing init')
    p.kill()


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

def test_filewatch(init):
    # First check that everything is ok.
    D.web_expect('all ok', LOCALHOST, '/', PORT)

    # check if file1 aging process
    touch(FILE1, -5)
    D.web_expect('all ok', LOCALHOST, '/', PORT)
    touch(FILE1, -15)
    D.web_expect('ERROR', LOCALHOST, '/', PORT)
    os.unlink(FILE1)
    D.web_expect('ERROR', LOCALHOST, '/', PORT)
    touch(FILE1)
    D.web_expect('all ok', LOCALHOST, '/', PORT)

    # test contents check for file2
    setfile(FILE2, 'xy')
    D.web_expect('all ok', LOCALHOST, '/', PORT)
    setfile(FILE2, 'ho-there xx 123')
    D.web_expect('ERROR', LOCALHOST, '/', PORT)
    setfile(FILE2, '')
    D.web_expect('all ok', LOCALHOST, '/', PORT)

    # create unexpected file in dir1
    touch(FILE1_1)
    D.web_expect('ERROR', LOCALHOST, '/', PORT)
    os.unlink(FILE1_1)
    D.web_expect('all ok', LOCALHOST, '/', PORT)

    # test dir2 newest check
    touch(FILE2_1, -15)
    D.web_expect('ERROR', LOCALHOST, '/', PORT)
    touch(FILE2_2)
    D.web_expect('all ok', LOCALHOST, '/', PORT)
