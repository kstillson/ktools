# kds circuitpython trivial web server
# adapted from https://github.com/deckerego/ampule; thanks deckerego!
# MIT license

# TODO: add POST submission parsing.


'''Trivial web-server for Circuit Python.
   Example usage in non-blocking mode:

import time
import kcore.webserver as W

def default_handler(request):
    name = request.get_params['name'] if 'name' in request.get_params else 'world'
    return f'Hello {name}!'

W.connect_wifi('dhcp-hostname', 'ssid', 'wifi-password')
svr = W.WebServer({'.*': default_handler}, 80)
while True:
    status = svr.listen()
    # That was non-blocking, we can do something else between incoming requests...
    print(f'{time.time()} - main loop; status={status}')
    time.sleep(0.5)  # Don't overwhelm serial monitor by looping too fast.
'''

import io, os, re, sys
import kcore.log_queue as Q
import kcore.webserver_base as B

PY_VER = sys.version_info[0]

# ----------
# Are we running CircuitPython? If not, inject path to the simulator.
import os, sys
CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')  # TODO: any better way?
if not CIRCUITPYTHON:
    simpath = os.path.join(os.path.dirname(__file__), 'circuitpy_sim')
    if not simpath in sys.path: sys.path.insert(0, simpath)
# ----------

import socketpool, wifi

MSG_DONTWAIT = 64   # from socket.MSG_DONTWAIT (so we don't have to import socket)

class WebServerCircPy(B.WebServerBase):
    def __init__(self, handlers={}, port=80,
                 listen_address='0.0.0.0', blocking=False, timeout=5, backlog_queue_size=3, socket=None,
                 *args, **kwargs):

        # Create a logging adapter that uses the low-dep system from kcore.log_queue.
        logging_adapter = B.LoggingAdapter(
            log_request=Q.log_info, log_404=Q.log_info,
            log_general=Q.log_info, log_exceptions=Q.log_error,
            get_logz_html=Q.last_logs_html)

        super(WebServerCircPy, self).__init__(handlers=handlers, logging_adapter=logging_adapter, *args, **kwargs)

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

        request = B.Request(method, full_path, remote_address=remote_address)
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

