
import pytest, sys, time
import kcore.webserver as W
import kcore.varz as V   # this is where the test plugin stores it stuff.

import context_hc  # fixes path
import hc

PORT = 62312   # Must match ../../testdata/home_control/hcdata_devices.py

TEST_SETTINGS = {
    'data_dir': ['testdata/home_control'],
    'debug': True,
    'plugins': ['plugin_web.py'],  # skip the other plugins...
}

@pytest.fixture(scope='session')
def init():
    # Register our TEST_SETTINGS
    hc.reset()  # clear out any other test's initialization...
    hc.control('doesnt', 'matter', TEST_SETTINGS)


# ---------- our test server

def start_test_server(port):
    handlers = { None: lambda request: test_handler(request) }
    ws = W.WebServer(handlers, port)
    ws.start()
    return ws


LAST_REQUEST = None
def test_handler(request):
    if not isinstance(request, W.Request): return '?'
    global LAST_REQUEST
    LAST_REQUEST = request
    if 'delay' in request.path: time.sleep(1)
    return 'ok'


# ---------- the tests

def test_delay_plugin(init):
    global LAST_REQUEST

    start_test_server(PORT)

    # ----- Test a foregrounded web request (debug mode).

    ok, details = hc.control('web1', 'test1')
    assert ok
    assert details == 'web1: ok [200]: ok'
    assert LAST_REQUEST.path == '/test1'

    # ----- Try a backgrounded request (non-debug mode).

    TEST_SETTINGS['debug'] = False
    LAST_REQUEST = '--'
    ok, details = hc.control('web1', 'delay1')
    assert LAST_REQUEST == '--'  # confirm not processed yet.
    assert ok
    assert 'background sent' in details

    time.sleep(2)
    assert LAST_REQUEST.path == '/delay1'  # confirm processed eventually.
