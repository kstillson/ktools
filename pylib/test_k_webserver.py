
import random, subprocess
import k_common as C
import k_webserver as W

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

def start(ctx={}):
    global PORT
    PORT = random_high_port()
    C.init_log('test_k_webserver', logfile=None)
    ws = W.WebServer(ROUTES, context=ctx)
    ws.start(port=PORT)
    return ws

def url(path): return 'http://localhost:%d/%s' % (PORT, path)

# ---------- tests

def test_basics():
    ws = start({'c': 'hello'})
    
    assert C.read_web(url('hi')) == 'hello world'

    resp = C.web_get(url('get?a=b&g=h&x=y'))
    assert resp.ok
    assert resp.status_code == 200
    assert resp.text == 'h'

    assert C.web_get(url('get'), get_dict={'g': 'h2'}).text == 'h2'

    assert C.web_get(url('post'), post_dict={'p': 'q'}).text == 'q'

    # Lets try POST queries constructed by curl rather than web_get
    assert subprocess.check_output(['curl', '-sS', '-d', 'x=y', url('post2')]) == b"{'x': 'y'}"
    assert subprocess.check_output(['curl', '-sS', '--form', 'a=b', url('post2')]) == b"{'a': ['b']}"
    
    assert C.web_get(url('context')).text == 'hello'

    assert C.web_get(url('match/v1')).text == 'v1'

