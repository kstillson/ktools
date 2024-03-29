
import http.server, pytest, random, ssl, sys, threading

import context_tools     # fix path to includes work as expected in tests
import kcore.auth

import kmc

# ----------

INCOMING_PATH = None            # What the webserver sees as its GET request path
PORT = random.randrange(10000, 19999)
RESP = (200, 'response-content')

# generate keyword args for the tests' query_km call.
KWARGS = {
    'km_host_port': 'localhost:%d' % PORT,
    'km_cert': 'testdata/server-cn=localhost.crt',
    'retry_delay': 0, 'retry_limit': 0 }

class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global INCOMING_PATH
        INCOMING_PATH = self.path
        self.send_response(RESP[0])
        self.end_headers()
        self.wfile.write(bytes(RESP[1], "utf-8"))

@pytest.fixture(scope='session')
def web_server():
    print('starting test webserver on port %d' % PORT, file=sys.stderr)
    server_address = ('localhost', PORT)
    httpd = http.server.HTTPServer(server_address, MyHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile='testdata/server-cn=localhost.pem')
    httpd.socket = ctx.wrap_socket(httpd.socket)
    # daemon thread will die when main program exits.
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

# ----------

def test_simple_successful_get_without_authn_check(web_server):
    global RESP
    RESP = (200, 'hello world')
    assert 'world' in kmc.query_km('keyname', **KWARGS)
    assert INCOMING_PATH.startswith('/keyname?a=v2')


def test_all_retries_fail(web_server):
    global RESP
    RESP = (401, 'error')
    assert kmc.query_km('key3', **KWARGS).startswith('ERROR')


def test_full_authn_cycle(web_server):
    global RESP
    RESP = (200, 'mysecret')
    # as client
    shared_secret_str = kcore.auth.generate_shared_secret()
    answer = kmc.query_km('key4', **KWARGS)

    # now let's perform the server-side authN check logic
    # (our simplistic server has already given up the secret, but we can
    #  still test now whether what it should have done would have worked).
    path, token = INCOMING_PATH.split('?a=', 1)
    assert path == '/key4'
    rslt = kcore.auth.verify_token_given_shared_secret(token, 'key4', shared_secret_str, client_addr=None)
    assert rslt.ok
    assert rslt.status == 'ok'
    assert not rslt.username

    # and finally check the client got the expected answer
    assert answer == 'mysecret'


# same test as above, but use a password (and no username).
def test_full_authn_cycle_with_password(web_server):
    global RESP
    RESP = (200, 'mysecret')
    shared_secret_str = kcore.auth.generate_shared_secret(user_password='pass123')

    # Let's try it with no password and confirm it fails.
    answer = kmc.query_km('key5', **KWARGS)
    path, token = INCOMING_PATH.split('?a=', 1)
    rslt = kcore.auth.verify_token_given_shared_secret(token, 'key5', shared_secret_str, client_addr=None, must_be_later_than_last_check=False)
    assert not rslt.ok
    assert 'fails to verify' in rslt.status

    # And try again with the wrong password and confirm it fails.
    answer = kmc.query_km('key5', password='wrong-password', **KWARGS)
    path, token = INCOMING_PATH.split('?a=', 1)
    rslt = kcore.auth.verify_token_given_shared_secret(token, 'key5', shared_secret_str, client_addr=None, must_be_later_than_last_check=False)
    assert not rslt.ok
    assert 'fails to verify' in rslt.status

    # And finally use the right password and make sure it works.
    answer = kmc.query_km('key5', password='pass123', **KWARGS)
    path, token = INCOMING_PATH.split('?a=', 1)
    rslt = kcore.auth.verify_token_given_shared_secret(token, 'key5', shared_secret_str, client_addr=None, must_be_later_than_last_check=False)
    assert rslt.ok
    assert rslt.status == 'ok'
    assert answer == 'mysecret'
