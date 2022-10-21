'''
NB: This launches a real web-server and talks to it via the local
network.  Tests will fail if firewall rules don't allow localhost high
port connections.
'''

import context_kcore     # fix path to includes work as expected in tests

import random
import kcore.common as C
import kcore.webserver as W
import kcore.varz_prom as V

# ---------- helpers

HEALTHZ_OUT = 'all ok'
def healthz_handler(request): return HEALTHZ_OUT

def random_high_port(): return random.randrange(10000, 19999)

def start():
    global PORT
    PORT = random_high_port()
    ## C.init_log('test_k_webserver', logfile=None) # filter_level_stderr=C.DEBUG)
    ws = W.WebServer({'/healthz': healthz_handler})
    ws.start(port=PORT)
    return ws

def url(path, tls=False):
    protocol = 'https' if tls else 'http'
    return '%s://localhost:%d/%s' % (protocol, PORT, path)

# ---------- tests

def test_basics():
    ws = start()
    V.init(ws)

    V.set('counter1', 3)
    V.bump('counter1')
    V.set('info1', 'value1')
    V.stamp('stamp1')

    assert C.read_web(url('healthz')) == 'all ok'

    metrics = C.read_web(url('metrics'))
    assert 'varz_counter1{program="/usr/bin/pytest-3"} 4.0' in metrics
    assert 'varz_info1_info{program="/usr/bin/pytest-3",value="value1"} 1.0' in metrics
    assert 'varz_stamp1_total{program="/usr/bin/pytest-3"} 1.0' in metrics
    assert 'varz_stamp1_created{program="/usr/bin/pytest-3"}' in metrics
    assert 'healthz_info{program="/usr/bin/pytest-3",value="all ok"} 1.0' in metrics
    assert 'healthz_status{program="/usr/bin/pytest-3"} 0.0' in metrics

    global HEALTHZ_OUT
    HEALTHZ_OUT = 'error1'    
    V.inc('counter1', add=10)
    V.set('info1', 'value2')
    V.stamp('stamp1')

    assert C.read_web(url('healthz')) == 'error1'

    metrics = C.read_web(url('metrics'))
    import sys
    assert 'varz_counter1{program="/usr/bin/pytest-3"} 14.0' in metrics
    assert 'varz_info1_info{program="/usr/bin/pytest-3",value="value2"} 1.0' in metrics
    assert 'varz_stamp1_total{program="/usr/bin/pytest-3"} 2.0' in metrics
    assert 'healthz_info{program="/usr/bin/pytest-3",value="error1"} 1.0' in metrics
    assert 'healthz_status{program="/usr/bin/pytest-3"} 1.0' in metrics
