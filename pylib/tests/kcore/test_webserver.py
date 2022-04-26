'''
NB: This launches a real web-server and talks to it via the local
network.  Tests will fail if firewall rules don't allow localhost high
port connections.
'''

import context_kcore     # fix path to includes work as expected in tests

import random, subprocess
import kcore.common as C
import kcore.webserver as W

# ---------- helpers

ROUTES = {
    '/hi':       lambda _: 'hello world',
    '/context': lambda request: request.context.get('c'),
    '/get':     lambda request: request.get_params.get('g'),
    '/post':    lambda request: request.post_params.get('p'),
    '/post2':   lambda request: str(request.post_params),
    r'/match/(\w+)': lambda request: request.route_match_groups[0],
}

def random_high_port(): return random.randrange(10000, 19999)

def start(ctx={}, start_kwargs={}):
    global PORT
    PORT = random_high_port()
    C.init_log('test_k_webserver', logfile=None)
    ws = W.WebServer(ROUTES, context=ctx)
    ws.start(port=PORT, **start_kwargs)
    return ws

def url(path, tls=False):
    protocol = 'https' if tls else 'http'
    return '%s://localhost:%d/%s' % (protocol, PORT, path)

# ---------- tests

def test_basics():
    ws = start({'c': 'hello'})
    
    assert C.read_web(url('hi')) == 'hello world'

    resp = C.web_get_e(url('get?a=b&g=h&x=y'))
    assert resp.ok
    assert resp.status_code == 200
    assert resp.text == 'h'

    assert C.web_get_e(url('get'), get_dict={'g': 'h2'}).text == 'h2'

    assert C.web_get_e(url('post'), post_dict={'p': 'q'}).text == 'q'

    # Lets try POST queries constructed by curl rather than web_get
    assert subprocess.check_output(['curl', '-sS', '-d', 'x=y', url('post2')]) == b"{'x': 'y'}"
    assert subprocess.check_output(['curl', '-sS', '--form', 'a=b', url('post2')]) == b"{'a': ['b']}"
    
    assert C.web_get_e(url('context')).text == 'hello'

    assert C.web_get_e(url('match/v1')).text == 'v1'

# TODO: test shutdown


def test_tls():
    ws = start({},
               {'tls_cert_file': 'testdata/server-cn=localhost.crt',
                'tls_key_file': 'testdata/server-cn=localhost.pem'})
    my_url = url('hi', tls=True)
    assert 'https' in my_url
    got = C.web_get_e(my_url, verify_ssl=True, cafile='testdata/server-cn=localhost.crt')
    assert got.text == 'hello world'
