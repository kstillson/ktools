
import pytest, random, sys, time
import kcore.webserver as W
import kcore.varz as V   # this is where the test plugin stores it stuff.

import context_hc  # fixes path
import hc


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
    print(f'start test server on port {port}', file=sys.stderr)
    ws = W.WebServer(handlers, port)
    ws.start()
    return ws


HANDLER_DELAY = 0
LAST_REQUEST = None
def test_handler(request):
    if not isinstance(request, W.Request): return '?'  # Test seems to pass a RequestFramework object occasionally; no idea what/why that is.  Ignore it seems to work.
    global LAST_REQUEST
    LAST_REQUEST = request
    time.sleep(HANDLER_DELAY)
    return 'ok'


# ---------- the tests

def test_delay_plugin(init):
    global HANDLER_DELAY, LAST_REQUEST

    random_high_port = random.randrange(10000, 19999)
    random_high_port_str = str(random_high_port)
    start_test_server(random_high_port)

    # ----- Test a foregrounded web request (debug mode).

    ok, details = hc.control('web1', random_high_port_str)
    assert ok
    assert details == 'web1: ok [200]: ok'
    assert LAST_REQUEST.path == '/' + random_high_port_str

    # ----- Try a backgrounded request (non-debug mode).

    TEST_SETTINGS['debug'] = False
    HANDLER_DELAY = 2
    LAST_REQUEST = '--'
    ok, details = hc.control('web1', random_high_port_str)
    assert LAST_REQUEST == '--'  # confirm not processed yet.
    assert ok
    assert 'background sent' in details

    time.sleep(2)
    assert LAST_REQUEST.path == '/' + random_high_port_str  # confirm processed eventually.
