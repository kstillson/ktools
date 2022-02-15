# kds circuitpython trivial web server
# adapted from https://github.com/deckerego/ampule; thanks deckerego!
# MIT license

'''Trivial web-server for Circuit Python.
   Example usage in non-blocking mode:


def default_handler(request):
    name = request.params['name'] if 'name' in request.params else 'world'
    return f'Hello {name}!'

kds_cp_web_server.connect_wifi('dhcp-hostname', 'ssid', 'wifi-password')
svr = kds_cp_web_server.WebServer(80)  ## Non-blocking mode by default.
svr.add_handler('/', default_handler)

while True:
    status = svr.listen()
    # That was non-blocking, we can do something else between incoming requests...
    print(f'{time.time()} - main loop; status={status}')
    time.sleep(0.5)  # Don't overwhelm serial monitor by looping too fast.
'''

import io, os, re, sys

# Are we running CircuitPython? If not, add path to circ-py simulator.
CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')  # TODO: any better way?
if not CIRCUITPYTHON: sys.path.insert(0, 'circpysim')

import socketpool, wifi  # Circuitpython specific

BUFFER_SIZE = 256
VARIABLE_RE = re.compile("^<([a-zA-Z]+)>$")


# A populated instance of this class is passed to handlers.
class Request:
    def __init__(self, method, full_path, remote_address):
        self.method = method
        self.path = full_path.split("?")[0]
        self.params = Request.__parse_params(full_path)
        self.headers = {}
        self.remote_address = remote_address
        self.body = None

    @staticmethod
    def __parse_params(path):
        query_string = path.split("?")[1] if "?" in path else ""
        param_list = query_string.split("&")
        params = {}
        for param in param_list:
            key_val = param.split("=")
            if len(key_val) == 2:
                params[key_val[0]] = key_val[1]
        return params


# Response:
# Handlers return: html_content (a string)
#              or: (html_content, http_return_code)
#              or: (html_content, http_return_code, reply_headers_dict)
# (default return code is 200, default is only minimal default headers).

class WebServer:
    
    # ------------------------------
    # public api

    def __init__(self, port=None, timeout=30,
                 # If blocking, self.listen() blocks until client connects.
                 # If not blocking, self.listen() returns and you can do something else while waiting for clients.
                 blocking=False, bind_address='0.0.0.0',
                 # Consider larger backlog_queue_size if self.listen() isn't called quite frequently.
                 backlog_queue_size=3,
                 # Generally you want handlers wrapped so an error during processing doesn't crash everything.
                 # But during debugging, the stack trace from an unhandled exception can be quite handy.
                 wrap_handlers=True,
                 # Here for testing, normally let the code below create the socket.
                 socket=None):
        if not port: port = 80 if CIRCUITPYTHON else 8080
        self.routes = []
        self.timeout = timeout
        self.wrap_handlers = wrap_handlers
        if not socket:
            pool = socketpool.SocketPool(wifi.radio)
            self.socket = pool.socket()
        else:
            self.socket = socket
        self.socket.bind((bind_address, port))
        self.socket.listen(backlog_queue_size)
        self.socket.setblocking(blocking)

    # Returns: -3 if no suitable handler was found
    #          -2 if problem with socket (unlikely to recover)
    #          -1 if exception during handler
    #           0 if non-blocking and no client connected yet
    #           1 if handler ran ok.
    def listen(self):
        try:
            client, remote_address = self.socket.accept()
        except OSError as e:
            if e.args[0] == 11: return 0  # errno.EAGAIN
            else: return -2
        if self.wrap_handlers:
            try:
                ok = self._read_and_process_request(client, remote_address)
            except BaseException as e:
                print("Error with request:", e)
                self._send_response(client, "Error processing request", 500, {})
                return -1
        else:
            ok = self._read_and_process_request(client, remote_address)
        client.close()
        return 1 if ok else -3

    def add_handler(self, rule, handler, method='GET'):
        self._on_request(method, rule, handler)
        
    
    # ------------------------------
    # Internals

    def _read_and_process_request(self, client, remote_address):
        client.settimeout(self.timeout)
        request = self._read_request(client, remote_address)
        match = self._match_route(request.path, request.method)
        if match:
            args, route = match
            answer = route["func"](request, *args)
            if type(answer) == tuple:
                body = answer[0]
                status = answer[1] if len(answer) > 1 else 200
                headers = answer[2] if len(answer) > 2 else {}
            else:
                body = answer
                status = 200
                headers = {}
            self._send_response(client, body, status, headers)
            return True
        else:
            self._send_response(client, "Not found", 404, {})
            return False
        
                              
    def _parse_headers(self, reader):
        headers = {}
        for line in reader:
            if line == b'\r\n': break
            title, content = str(line, "utf-8").split(":", 1)
            headers[title.strip().lower()] = content.strip()
        return headers
    
    def _parse_body(self, reader):
        data = bytearray()
        for line in reader:
            if line == b'\r\n': break
            data.extend(line)
        return str(data, "utf-8")
    
    def _read_request(self, client, remote_address):
        message = bytearray()
        client.settimeout(self.timeout)
        socket_recv = True
        try:
            while socket_recv:
                buffer = bytearray(BUFFER_SIZE)
                client.recv_into(buffer)
                start_length = len(message)
                for byte in buffer:
                    if byte == 0x00:
                        socket_recv = False
                        break
                    else:
                        message.append(byte)
        except OSError as error:
            print("Error reading from socket", error)
    
        reader = io.BytesIO(message)
        line = str(reader.readline(), "utf-8")
        (method, full_path, version) = line.rstrip("\r\n").split(None, 2)
    
        request = Request(method, full_path, remote_address)
        request.headers = self._parse_headers(reader)
        request.body = self._parse_body(reader)
    
        return request
    
    def _send_response(self, client, data, return_code, headers={}):
        headers["Server"] = "kds-eb-server (CircuitPython)"
        headers["Connection"] = "close"
        headers["Content-Length"] = len(data)
    
        response = "HTTP/1.1 %i OK\r\n" % return_code
        for k, v in headers.items():
            response += "%s: %s\r\n" % (k, v)
        response += "\r\n" + data + "\r\n"
    
        # unreliable sockets on ESP32-S2: see https://github.com/adafruit/circuitpython/issues/4420#issuecomment-814695753
        response_length = len(response)
        bytes_sent_total = 0
        while True:
            try:
                bytes_sent_total += client.send(bytes(response, 'utf-8'))
                if bytes_sent_total >= response_length:
                    return bytes_sent_total
                else:
                    response = response[bytes_sent:]
                    continue
            except OSError as e:
                if e.errno == 11:       # EAGAIN: no bytes have been transfered
                    continue
                else:
                    return bytes_sent_total
    
    def _on_request(self, method, rule, request_handler):
        regex = "^"
        rule_parts = rule.split("/")
        for part in rule_parts:
            # Is this portion of the path a variable?
            var = VARIABLE_RE.match(part)
            if var:
                # If so, allow any alphanumeric value
                regex += r"([a-zA-Z0-9_-]+)\/"
            else:
                # Otherwise exact match
                regex += part + r"\/"
        regex += "?$"
        self.routes.append(
            (re.compile(regex), {"method": method, "func": request_handler})
        )
    
    def _match_route(self, path, method):
        for matcher, route in self.routes:
            match = matcher.match(path)
            if match and method == route["method"]:
                return (match.groups(), route)
        return None


# --------------------
# Helper to connect to wifi.  Returns (mac, ip)

def connect_wifi(dhcp_hostname, ssid, wifi_password, print_addrs=True):
    wifi.radio.hostname = dhcp_hostname
    wifi.radio.connect(ssid, wifi_password)
    if print_addrs:
        print("MAC: ", [hex(i) for i in wifi.radio.mac_address])
        print("IP: ", wifi.radio.ipv4_address)
    return (wifi.radio.mac_address, wifi.radio.ipv4_address)
    
