#!/usr/bin/python3

import pytest, tempfile, time
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_gift_coord(container_to_test):
    time.sleep(3)  # Give things a chance to start-up.
    ip = container_to_test.ip

    # Check our overall health is good.
    D.web_expect('ok', ip, '/healthz', 8080)

    # Switch to curl to use cookies
    with tempfile.NamedTemporaryFile() as tf:
        cookie_jar = tf.name
        D.popen_expect(['curl', '-v', '-L', '-c', cookie_jar, f'http://{ip}:8080/'],
                       'login')
        D.popen_expect(['curl', '-v', '-b', cookie_jar, '-d', 'user=Ken', f'http://{ip}:8080/login'],
                       'successful login')
        D.popen_expect(['curl', '-v', '-b', cookie_jar, f'http://{ip}:8080/'],
                       'hello Ken')
        D.popen_expect(['curl', '-v', '-b', cookie_jar, '-d', 'user=Nanny&item=item1&taken=hold&notes=notes1&url=url1', f'http://{ip}:8080/add'],
                       'successful add')
        D.popen_expect(['curl', '-v', '-b', cookie_jar, f'http://{ip}:8080/'],
                       'item1')
