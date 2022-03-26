
import http.server, pytest, random, ssl, sys, threading
import k_auth

import context       # includes ../ in path so we can import things there.
import kmc

# ----------

INCOMING_PATH = None            # What the webserver sees as its GET request path
PORT = random.randrange(20000, 30000)
RESP = (200, 'response-content')

# generate keyword args for the tests' query_km call.
KWARGS = {
    'km_host_port': 'localhost:%d' % PORT,
    'keyname_prefix': 'test-',
    'km_cert': 'tests/server.crt',
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
    httpd.socket = ssl.wrap_socket(
        httpd.socket, server_side=True,
        certfile='tests/server.pem', ssl_version=ssl.PROTOCOL_TLS)
    # daemon thread will die when main program exits.
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

# ----------

def test_simple_successful_get_without_authn_check(web_server):
    global RESP
    RESP = (200, 'hello world')
    assert 'world' in kmc.query_km('keyname', **KWARGS)
    assert INCOMING_PATH.startswith('/test-keyname?a=v2')

    
def test_all_retries_fail(web_server):
    global RESP
    RESP = (401, 'error')
    assert kmc.query_km('key3', **KWARGS) is None


def test_full_authn_cycle(web_server):
    global RESP
    RESP = (200, 'mysecret')
    # as client
    reg_blob = k_auth.generate_client_registration()
    answer = kmc.query_km('key4', **KWARGS)
    
    # now let's perform the server-side authN check logic
    # (our simplistic server has already given up the secret, but we can
    #  still test now whether what it should have done would have worked).
    path, token = INCOMING_PATH.split('?a=', 1)
    assert path == '/test-key4'
    okay, status, hostname, username, sent_time = k_auth.validate_token_given_registration(token, 'test-key4', reg_blob)
    assert status == 'ok'
    assert okay
    assert not username
    
    # and finally check the client got the expected answer
    assert answer == 'mysecret'


# same test as above, but use a password (and no username).
def test_full_authn_cycle_with_password(web_server):
    global RESP
    RESP = (200, 'mysecret')
    reg_blob = k_auth.generate_client_registration(user_password='pass123')

    # Let's try it with no password and confirm it fails.
    answer = kmc.query_km('key5', **KWARGS)
    path, token = INCOMING_PATH.split('?a=', 1)
    okay, status, hostname, username, sent_time = k_auth.validate_token_given_registration(token, 'test-key5', reg_blob, must_be_later_than_last_check=False)
    assert 'fails to validate' in status
    assert not okay

    # And try again with the wrong password and confirm it fails.
    answer = kmc.query_km('key5', password='wrong-password', **KWARGS)
    path, token = INCOMING_PATH.split('?a=', 1)
    okay, status, hostname, username, sent_time = k_auth.validate_token_given_registration(token, 'test-key5', reg_blob, must_be_later_than_last_check=False)
    assert 'fails to validate' in status
    assert not okay

    # And finally use the right password and make sure it works.
    answer = kmc.query_km('key5', password='pass123', **KWARGS)
    path, token = INCOMING_PATH.split('?a=', 1)
    okay, status, hostname, username, sent_time = k_auth.validate_token_given_registration(token, 'test-key5', reg_blob, must_be_later_than_last_check=False)
    assert status == 'ok'
    assert okay
    assert answer == 'mysecret'
