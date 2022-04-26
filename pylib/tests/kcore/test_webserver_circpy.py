
# NB: This launches a real web-server and talks to it via the network.
# Tests will fail if firewall rules don't allow that.

# By default, launches the webserver specified in server.py:create_ws()
# on a local random high port, and tests against that.  This is basically
# testing circuitpy_sim to see if it can start a CPython server that
# convinces this test.

# To run the same test against real hardware, copy the file server.py to
# code.py on your device, and wait for the server to start up.  It should
# print it's IP address.  Set that IP address in the environment variable
# TESTHOST, and then run this test script under pytest-3.

import context_kcore   # fixup Python include path

import os, pytest, random, threading, subprocess
import kcore.common as C

# ---------- server fixture

def listen_loop(ws):
    while True: ws.listen()


@pytest.fixture(scope='session')
def start_server():
    testhost = os.environ.get('TESTHOST', None)

    # If $TESTHOST is defined, we're going to use that external server
    # (presumably running on real Circuit Python hardware) as our backend.
    if testhost:
        base_url = f'http://{testhost}:80/'
        C.stderr(f'testing against external host: {base_url}')
        return base_url

    # Otherwise, we're going to start a local instance of the (blocking)
    # server.py and run it ourselves on a background thread.
    import server
    random_high_port = random.randrange(10000, 19999)
    base_url = f'http://localhost:{random_high_port}/'
    C.stderr(f'testing against internal loopback server: {base_url}')
    ws = server.create_ws(random_high_port)
    t= threading.Thread(target=listen_loop, args=(ws,), daemon=True).start()
    return base_url
    

# ---------- tests

def test_webserver_basics(start_server):
    base_url = start_server
    localhost = 'localhost' in base_url

    # check the most basic 'hello wworld' handler.
    assert C.read_web(base_url + 'hi', wrap_exceptions=False) == 'hello world'

    # check the get param parser (which returns the value of "g")
    resp = C.web_get(base_url + 'get?a=b&g=h&x=y')
    assert resp.ok
    assert resp.status_code == 200
    assert resp.text == 'h'

    # same as above but letting web_get construct the get params.
    assert C.web_get(base_url + 'get', get_dict={'g': 'h2'}).text == 'h2'

    # check web context and field group matching.
    assert C.web_get(base_url + 'context').text == 'hello'
    assert C.web_get(base_url + 'match/v1').text == 'v1'

    # check getting an invalid page
    assert C.web_get(base_url + 'invalid').status_code == 404

    # check remote adderss parsing
    ra_tuple_str = C.web_get(base_url + 'ra').text
    C.stderr(f'got remote address: {ra_tuple_str}')
    _, ra_ip, _2 = ra_tuple_str.split("'", 2)
    if localhost:
        # When testing via loopback, our "remote" address should be loopback'd.
        assert ra_ip == '127.0.0.1'
    else:
        # We don't know what our IP address will appear to be on the remote
        # host.  So let's just confirm it looks vaguely like an IP address.
        assert ra_ip.count('.') == 3


def test_suite_for_kcore(start_server):
    base_url = start_server
    localhost = 'localhost' in base_url

    # check varz (both set and retrieve).
    assert C.web_get(base_url + 'vset?a=b').text == '1'
    assert C.web_get(base_url + 'varz?a').text == 'b'

    # check gpio.KButton (D0 should be floating high), passed via context.
    assert C.read_web(base_url + 'kb1') == 'True'
    
    # check html.
    assert C.read_web(base_url + 'hi2') == '<p>hello world</p>\n'

    # check logging and in-memory log queue.
    assert C.read_web(base_url + 'logfun') == 'ok'
    assert 'logfun' in C.read_web(base_url + 'logz')

    # try setting a neopixel (can't test if it worked, but at least test
    # it doesn't crash...)
    assert 'ok' == C.read_web(base_url + 'neoflash')

    
