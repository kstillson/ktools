
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

import context_circuitpy_lib   # fixup Python include path

import os, random, threading, subprocess
import common_circpy as C
import server

# ---------- helpers

def listen_loop(ws):
    while True: ws.listen()

BASE_URL = None
def url(path): return BASE_URL + path

# ---------- tests

def test_basics():
    # Figure out if we're running on a local circuitpy_sim server which we start,
    # or an external server where we've been given the hostname.
    global BASE_URL
    testhost = os.environ.get('TESTHOST', None)
    if testhost:
        BASE_URL = f'http://{testhost}:80/'
        C.stderr(f'testing against external host: {BASE_URL}')
    else:
        random_high_port = random.randrange(10000, 19999)
        BASE_URL = f'http://localhost:{random_high_port}/'
        C.stderr(f'testing against internal loopback server: {BASE_URL}')
        # Now start that blocking server on a separate thread.
        ws = server.create_ws(random_high_port)
        t= threading.Thread(target=listen_loop, args=(ws,))
        t.daemon = True
        t.start()

    # ---------- The actual tests
    
    assert C.read_web(url('hi'), wrap_exceptions=False) == 'hello world'

    resp = C.web_get(url('get?a=b&g=h&x=y'))
    assert resp.ok
    assert resp.status_code == 200
    assert resp.text == 'h'

    assert C.web_get(url('invalid')).status_code == 404
    
    assert C.web_get(url('get'), get_dict={'g': 'h2'}).text == 'h2'
    assert C.web_get(url('context')).text == 'hello'
    assert C.web_get(url('match/v1')).text == 'v1'

    ra_tuple_str = C.web_get(url('ra')).text
    C.stderr(f'got remote address: {ra_tuple_str}')
    _, ra_ip, _2 = ra_tuple_str.split("'", 2)
    if testhost:
        # We don't know what our IP address will appear to be on the remote
        # host.  So let's just confirm it looks vaguely like an IP address.
        assert ra_ip.count('.') == 3
    else:
        # When testing via loopback, our "remote" address should be loopback'd.
        assert ra_ip == '127.0.0.1'
