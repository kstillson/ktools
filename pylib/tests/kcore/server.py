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

'''

import time
import kcore.webserver_circpy as W

ROUTES = {
    '/context':      lambda request: request.context.get('c'),
    '/get':          lambda request: request.get_params.get('g'),
    '/hi':           lambda _: 'hello world',
    r'/match/(\w+)': lambda request: request.route_match_groups[0],
    '/ra':           lambda request: str(request.remote_address),
}

def create_ws(port):
    ctx = {'c': 'hello'}
    ws = W.WebServer(ROUTES, port=port, blocking=True, context=ctx)
    return ws


def main():
    print(f'{time.time()}: connecting to wifi...')
    W.connect_wifi('dhcp_hostname', 'ssid', 'wifi_password')
    ws = create_ws(80)
    print(f'{time.time()}: starting web server')
    while True:
        status = ws.listen()
        print(f'{time.time()}: main loop; status={status}')
        time.sleep(0.5)  # Don't overwhelm serial monitor by looping too fast if we end up in non-blocking mode.


if __name__ == '__main__':
    main()
