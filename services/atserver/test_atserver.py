
import pytest, random, sys, threading, time
import kcore.common as C
import kcore.webserver as W
import atserver as A


# ---------- testing infrastructure

@pytest.fixture(scope='module')
def setup_test():
    # Log to stdout (for easier test debugging)
    C.init_log('debug log', '-', filter_level_logfile=C.DEBUG)


# ---------- our test server

def start_test_server(port: int):
    handlers = { None: lambda request: server_handler(request) }
    print(f'start test server on port {port}', file=sys.stderr)
    ws = W.WebServer(handlers, port)
    ws.start()
    return ws


PENDING_FAILS = 0
def server_handler(request):
    if not isinstance(request, W.Request): return '?'  # Test seems to pass a RequestFramework object occasionally; no idea what/why that is.  Ignore it seems to work.

    global PENDING_FAILS
    if PENDING_FAILS > 0:
        PENDING_FAILS -= 1
        C.log('TEST SERVER: RETURNING FAILURE AS REQUESTED')
        return 'error- pending failure requested'

    return 'ok'


# ---------- tests

def test_primary(setup_test, tmp_path):
    persist_file = str(tmp_path / 'atserver_test.persist')

    # start the http server we'll send out get requests to
    global PENDING_FAILS
    PENDING_FAILS = 1
    http_server_port = random.randrange(10000, 19999)
    start_test_server(http_server_port)
    url = f'http://localhost:{http_server_port}/'

    TESTING_ARGS = [
        '--debug',
        '--filename', persist_file,
        '--logfile', '-',
        '--default_output', 'log',
        '--default_retries', '2',
        '--retry_secs', '1', ]

    # start the atserver
    A.LOOP_TIME = 1
    atserver_port = random.randrange(10000, 19999)
    thread = threading.Thread(
        target=A.main,
        args=[TESTING_ARGS + ['--port', str(atserver_port)]])
    thread.daemon = True
    thread.start()

    # add first event via a simulated CLI call.
    # should fail once due to PENDING_FAILS=1, then succeed on retry after 1s.
    rtn = A.main(TESTING_ARGS + [
        '--add',
        '--name', 'test1',
        '--time', 'now',
        '--url', url])
    assert rtn == 0
    assert A.V.get('added:ok') == 1

    # add second event via http form
    resp = C.web_get(f'http://localhost:{atserver_port}/add', post_dict={
        'when1': 'now',
        'when2': '1s',
        'name': 'test2',
        'quiet': '1',
        'action': 'url',
        'url': url})
    assert resp.ok
    assert A.V.get('added:ok') == 2

    time.sleep(4)

    # check results via varz
    assert A.V.get('added:ok') == 3   # 2 orig + 1 retry
    assert A.V.get('mapped-ok-to-error') == 1
    assert A.V.get('fired:ok') == 2
    assert A.V.get('fired:error') == 1
    assert A.V.get('retries-queued') == 1
