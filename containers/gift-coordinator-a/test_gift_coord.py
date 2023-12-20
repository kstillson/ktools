#!/usr/bin/python3

import pytest, tempfile, time
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


def skip_if(): return D.check_env_for_prod_mode() and D.not_required_host('a1')


# ---------- tests

@pytest.mark.skipif(skip_if(), reason='prod test requires host a1')
def test_gift_coord(container_to_test):
    time.sleep(5)  # Give things a chance to start-up.
    ip = 'localhost'
    port = 8100 + container_to_test.port_shift

    # Check our overall health is good.
    D.web_expect('ok', ip, '/healthz', port)

    # Switch to curl to use cookies
    with tempfile.NamedTemporaryFile() as tf:
        cookie_jar = tf.name
        D.popen_expect(['curl', '-v', '-L', '-c', cookie_jar, f'http://{ip}:{port}/'],
                       'login')
        D.popen_expect(['curl', '-v', '-b', cookie_jar, '-d', 'user=Ken', f'http://{ip}:{port}/login'],
                       'successful login')
        D.popen_expect(['curl', '-v', '-b', cookie_jar, f'http://{ip}:{port}/'],
                       'hello Ken')
        D.popen_expect(['curl', '-v', '-b', cookie_jar, '-d', 'user=Nanny&item=item1&taken=hold&notes=notes1&url=url1', f'http://{ip}:{port}/add'],
                       'successful add')
        D.popen_expect(['curl', '-v', '-b', cookie_jar, f'http://{ip}:{port}/'],
                       'item1')
