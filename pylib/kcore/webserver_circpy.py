'''Simple web-server for Circuit Python.

Adapted from https://github.com/deckerego/ampule; thanks deckerego!
MIT license

A great Google engineering best-practice I picked up while working there is
that just about *everything* should be a web server, and it's great to have
some standard handlers that just about everything supports, to help with
automated health checking and process management.  This module aims to provide
easy-to-use web server support on Circuit Python, with an API very similar to
that available with the normal full-Python version.

Circuit Python must use non-blocking mode, because it doesn't support multiple
threads.  Here's an example:

  import time
  import kcore.webserver_circpy as W

  def default_handler(request):
    return f"Hello {request.get_params['name'] or 'world'}!"

  W.connect_wifi('desired-dhcp-hostname', 'ssid', 'wifi-password')
  svr = W.WebServer({None: default_handler}, port=80)
  while True:
    status = svr.listen()
    # That was non-blocking, we can do something else between incoming requests...
    print(f'{time.time()} - main loop; status={status}')
    time.sleep(0.5)  # Don't overwhelm serial monitor by looping too fast.


This module is built on-top of webserver_base.py, so that much of the
handler-based business-logic can be shared with the full Python version in
webserver.py.

TODO: add POST submission parsing.  Currently this module inherets it's
GET parameter parsing from webserver_base.py, but I haven't yet attempted to
port webserverp.y:parse_port to Circuit Python.

'''

import io, os, re, sys
import kcore.common0 as C
from kcore.webserver_base import *

PY_VER = sys.version_info[0]

# ----------
# Are we running CircuitPython? If not, inject path to the simulator.
import os, sys
CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
if not CIRCUITPYTHON:
    simpath = os.path.join(os.path.dirname(__file__), '..', 'circuitpy_sim')
    if not simpath in sys.path: sys.path.insert(0, simpath)
# ----------

import socketpool, wifi

MSG_DONTWAIT = 64   # from socket.MSG_DONTWAIT (so we don't have to import socket)

class WebServer(WebServerBase):
    def __init__(self, handlers={}, port=80,
                 listen_address='0.0.0.0', blocking=False, timeout=5, backlog_queue_size=3, socket=None,
                 *args, **kwargs):

        # Create a logging adapter that uses the low-dep system from kcore.log_queue.
        logging_adapter = LoggingAdapter(
            log_request=C.log_info, log_404=C.log_info,
            log_general=C.log_info, log_exceptions=C.log_error,
            get_logz_html=C.last_logs_html)

        super(WebServer, self).__init__(handlers=handlers, logging_adapter=logging_adapter, *args, **kwargs)

        self.timeout = timeout
        if not socket:
            pool = socketpool.SocketPool(wifi.radio)
            self.socket = pool.socket()
        else:
            self.socket = socket
        self.logger.log_general('starting circpy webserver on port %d' % port)
        self.socket.bind((listen_address, port))
        self.socket.listen(backlog_queue_size)
        self.blocking = blocking
        self.socket.setblocking(blocking)

    # Returns: -3 if no suitable handler was found
    #          -2 if exception occured during other processing (not handler)
    #          -1 if exception during handler
    #           0 if non-blocking and no client connected yet
    #           1 if handler ran ok.
    def listen(self):
        try:
            client, remote_address = self.socket.accept()
        except OSError as e:
            if e.args[0] == 11: return 0  # errno.EAGAIN
            else: raise

        try:
            client.setblocking(self.blocking)
            request = self._read_request(client, remote_address)
        except Exception as e:
            self.logger.log_exceptions('error reading request: %s' % str(e))
            return -2
        response = self.find_and_run_handler(request)
        self._send_response(client, response)

        client.close()
        if response.exception: return -1
        if response.status_code == 404: return -3
        return 1

    # ------------------------------
    # Internals

    def _parse_headers(self, reader):
        headers = {}
        for line in reader:
            if line == b'\r\n': break
            if PY_VER == 3: line = str(line, 'utf-8')
            title, content = line.split(":", 1)
            headers[title.strip().lower()] = content.strip()
        return headers

    def _parse_body(self, reader):
        data = bytearray()
        for line in reader:
            data.extend(line)
        if PY_VER == 3: data = str(data, 'utf-8')
        return data

    def _read_request(self, client, remote_address=None):
        client.settimeout(self.timeout)
        message = bytearray()
        buffer_size = 4096
        buffer = bytearray(buffer_size)
        try:
            while True:
                got = client.recv_into(buffer)
                for byte in buffer: message.append(byte)   # circuitpython doesn't support bytearray.extend()
                if got < buffer_size: break
        except OSError as error:
            print("Error reading from socket: ", error)

        reader = io.BytesIO(message)
        line = reader.readline()
        if not line: line = reader.readline()
        if PY_VER == 3: line = str(line, "utf-8")

        (method, full_path, version) = line.rstrip("\r\n").split(None, 2)

        request = Request(method, full_path, remote_address=remote_address)
        request.headers = self._parse_headers(reader)
        request.body = self._parse_body(reader)
        return request

    def _send_response(self, client, response):
        headers = response.extra_headers.copy()
        headers["Server"] = "kds_webserver_circpy"
        headers["Connection"] = "close"
        headers["Content-Type"] = response.msg_type
        headers["Content-Length"] = len(response.body)

        out = "HTTP/1.1 %i %s\r\n" % (response.status_code, response.status_msg)
        for k, v in headers.items():
            out += "%s: %s\r\n" % (k, v)
        out += '\r\n'
        out1 = bytes(out) if PY_VER == 2 else bytes(out, 'utf-8')
        if response.binary: out2 = response.body
        elif PY_VER == 2: out2 = bytes(response.body)
        else: out2= bytes(response.body, 'utf-8')
        out = out1 + out2

        # unreliable sockets on ESP32-S2: see https://github.com/adafruit/circuitpython/issues/4420#issuecomment-814695753
        out_length = len(out)
        bytes_sent_total = 0
        while True:
            try:
                b = out # b = bytes(out) if PY_VER == 2 else bytes(out, 'utf-8')
                bytes_sent = client.send(b)
                bytes_sent_total += bytes_sent
                if bytes_sent_total >= out_length:
                    return bytes_sent_total
                else:
                    out = out[bytes_sent:]
                    continue
            except OSError as e:
                if e.errno == 11: continue      # EAGAIN: no bytes have been transfered
                else: return bytes_sent_total


# --------------------
# Helper to connect to wifi.  Returns (mac, ip)

def connect_wifi(dhcp_hostname, ssid, wifi_password, print_addrs=True):
    wifi.radio.hostname = dhcp_hostname
    wifi.radio.connect(ssid, wifi_password)
    if print_addrs:
        print("MAC: ", [hex(i) for i in wifi.radio.mac_address])
        print("IP: ", wifi.radio.ipv4_address)
    return (wifi.radio.mac_address, wifi.radio.ipv4_address)
