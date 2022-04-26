#!/usr/bin/python3
'''Server for test_k_webserver

By default, test_webserver_circpy uses webserver_circpy to launch the
webserver specified in this file, and then runs tests against that.

If you want to test against a webserver running on real circuit-py
hardware, Adjust the params to connect_wifi() [below], and then copy this
file to "code.py" on the device under test.  Turn on a serial monitor.

Once the device is connected to wifi, it should print its IP number.
On the Linux machine where you're going to run the tests, set
the IP number to the TESTHOST variable and run the test.  
i.e. something like:
   TESTHOST="192.168.9.99" pytest-3 tests/test_k_webserver_circpy.py

The server deliberately pulls in most of kcore.*, so test_webserver_circpy.py
can effectively test that kcore functionality works as expected in the limited
Python subset on a real circuit-python board.

'''

import os, sys, time
import kcore.webserver_circpy as W

import kcore.common as C
import kcore.html as H
import kcore.gpio as G
import kcore.neo as N
import kcore.varz as V

# circuitpy_sim
import board

CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')


# ---------- handlers

WEB_HANDLERS = {
    '/context':      lambda request: request.context.get('c'),
    '/get':          lambda request: request.get_params.get('g'),
    '/hi':           lambda request: 'hello world',
    '/hi2':          lambda request: H.wrap('hello world', 'p'),
    '/kb1':          lambda request: str(request.context.get('kb1').value()),
    '/logfun':       lambda request: logfun(request),
    r'/match/(\w+)': lambda request: request.route_match_groups[0],
    '/neoflash':     lambda request: neoflash(request),
    '/ra':           lambda request: str(request.remote_address),
    '/vset':         lambda request: vset(request),    
}


def logfun(request):
    C.clear_log()   # in-case it's gotten too long, and just to make sure it works.
    C.log('logfun')
    return 'ok'

    
def neoflash(request):
    neo = request.context.get('neo')
    neo[0] = N.RED
    time.sleep(0.2)
    neo[0] = N.GREEN
    time.sleep(0.2)
    neo[0] = N.PURPLE    
    time.sleep(0.2)
    neo[0] = N.OFF
    return 'ok'
    
    
def vset(request):
    for k, v in request.get_params.items(): V.set(k, v)
    return str(len(request.get_params))


# ---------- main

def create_ws(port):
    G.init()
    kb1 = G.KButton(board.D0, name='D0', background=not CIRCUITPYTHON)
    neo = N.Neo(n=1, pin=board.NEOPIXEL)
    ctx = {'c': 'hello', 'kb1': kb1, 'neo': neo}
    ws = W.WebServer(WEB_HANDLERS, wrap_handlers=False, port=port, blocking=True, context=ctx)
    return ws


# This part only runsif this file is main.py on real CircuitPy hardware.
# (when running locally, the test calls create_ws() direclty.
def main():
    try:
        import wifi_secrets as S
        print(f'{time.time()}: connecting to wifi...')
        W.connect_wifi(S.DHCP_HOSTNAME, S.SSID, S.WIFI_PASSWORD)
    except Exception as e:
        print('Unable to connect to wifi; skipping: ' + str(e), file=sys.stderr)
    
    ws = create_ws(port=8080)
    print(f'{time.time()}: starting web server')
    while True:
        status = ws.listen()
        print(f'{time.time()}: main loop; status={status}')
        time.sleep(0.3)  # Don't loop too fast...


if __name__ == '__main__':
    main()
