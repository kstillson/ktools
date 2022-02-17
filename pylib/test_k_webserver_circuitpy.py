
import random, threading, subprocess
import k_common as C
import k_webserver_circuitpy as W

# ---------- helpers

ROUTES = {
    '/hi':       lambda _: 'hello world',
    '/context': lambda request: request.context.get('c'),
    '/get':     lambda request: request.get_params.get('g'),
    r'/match/(\w+)': lambda request: request.route_match_groups[0],
}

def listen_loop(ws):
    while True:
        ws.listen()
        C.stderr('@@ listen loop')

def random_high_port(): return random.randrange(10000, 19999)

def start(ctx={}):
    global PORT
    PORT = random_high_port()
    C.init_log('test_k_webserver', logfile=None)
    ws = W.WebServer(ROUTES, port=PORT, blocking=True, context=ctx)
    return ws

def url(path): return 'http://localhost:%d/%s' % (PORT, path)

# ---------- tests

def test_basics():
    ws = start({'c': 'hello'})
    t= threading.Thread(target=listen_loop, args=(ws,))
    t.daemon = True
    t.start()
    
    assert C.read_web(url('hi')) == 'hello world'

    resp = C.web_get(url('get?a=b&g=h&x=y'))
    assert resp.ok
    assert resp.status_code == 200
    assert resp.text == 'h'

    assert C.web_get(url('get'), get_dict={'g': 'h2'}).text == 'h2'
    assert C.web_get(url('context')).text == 'hello'
    assert C.web_get(url('match/v1')).text == 'v1'
