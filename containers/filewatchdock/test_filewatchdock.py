#!/usr/bin/python3

# TODO: come up with test that isn't jack-configuration specific.

import atexit, os, pytest, subprocess, time, warnings
import kcore.docker_lib as D


# ---------- control constants

TOUCH_FILE = '/mnt/rsnap/daily.0/home/home/ken/share/tmp/touch'
TOUCH_FILE_BACKUP = '/mnt/rsnap/daily.0/home/home/ken/share/tmp/touch.mbk'


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- helpers

def cleanup():
    if not os.path.isfile(TOUCH_FILE_BACKUP): return
    subprocess.check_call(['/bin/cp', '-p', TOUCH_FILE_BACKUP, TOUCH_FILE])
    os.unlink(TOUCH_FILE_BACKUP)


# ---------- tests

@pytest.mark.skipif(D.not_required_host('jack'), reason='test contains host-specific configuration requirements')
def test_jack_filewatch(container_to_test):
    prod_mode = D.check_env_for_prod_mode()

    if prod_mode:
        D.web_expect('all ok', container_to_test.ip, '/', 8080)
        warnings.warn('filewatchdock test passed, but testing in prod mode is very limited (to avoid interference with production data')
        return

    atexit.register(cleanup)
    cleanup()       # If we had an unclean exit from a previous test.
    time.sleep(2)   # Allow for startup time.

    # First check that everything is ok.
    D.web_expect('all ok', container_to_test.ip, '/', 8080)

    # Backup tmp/touch file and set it's date to something old.
    subprocess.check_call(['/bin/cp', '-p', TOUCH_FILE, TOUCH_FILE_BACKUP])
    subprocess.check_call(['/usr/bin/touch', '-d', '20200101', TOUCH_FILE])
    D.web_expect('ERROR', container_to_test.ip, '/', 8080)

    # Put things back, and confirm everything is okay again.
    cleanup()
    D.web_expect('all ok', container_to_test.ip, '/', 8080)

