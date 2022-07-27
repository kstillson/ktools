'''A simplified web server, with a bunch of added features.

A great Google engineering best-practice I picked up while working there is
that just about *everything* should be a web server, and it's great to have
some standard handlers that just about everything supports, to help with
automated health checking and process management.  The goal here is that you
should be able to add a basic web-server with built-in standard handlers to
your program with ~2 lines of code:

  import webserver
  webserver.Webserver(port=8080).start()

And if you want to add your own custom handlers, it's just about as easy:

  import webserver
  def h_root(request): return "<p>Here is some html for the root page.</p>"
  def h_default(request): return webserver.Response('dunno how to do that', 401)
  webserver.WebServer(port=8080, handlers={'/': h_root, None: h_default }).start()

(Note that handlers can return plain text, HTML, or a Response object.  Nice, huh?)

I really wanted a web-server with (basically) the same API for Python 2,
Python 3, and Circuit Python.  However the latter doesn't support threads and
has only quite low-level networking.  So, the functionality is split like this:

- webserver_base.py has most of the business logic for things like finding and
  running handlers, but knows nothing about networking or threads.  It has an
  abstraction for Requests and Responses, and it works by manipulating these
  abstractions.  It just has no idea how they get sent or received.

- This file (webserver.py) adds on standard Python ("CPython") networking
  (including support for TLS; i.e. certficiate protected https), and threading.

- webserver_circpy.py is also built on webserver_base.py, and links in the
  low-level networking support for Circuit Python, and a non-blocking "listen"
  interface, which can be used for cooperative multitasking.

'''

import cgi, threading, ssl, sys

import kcore.common as C             # for logging.
from kcore.webserver_base import *   # you can use Request/Response without separately importing webserver_base.

PY_VER = sys.version_info[0]
if PY_VER == 2:
    from urlparse import parse_qs
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    DEFAULT_SERVER_CLASS = HTTPServer
else:
    from urllib.parse import parse_qs
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    DEFAULT_SERVER_CLASS = ThreadingHTTPServer


class Worker(BaseHTTPRequestHandler):
    def send(self, response):
        if PY_VER == 3: response.body = response.body.encode('utf-8')
        self.send_response(response.status_code, response.status_msg)
        self.send_header("Server", 'k_webserver')
        self.send_header("Connection", 'close')
        self.send_header("Content-type", response.msg_type)
        self.send_header("Content-Length", len(response.body))
        for k, v in response.extra_headers.items(): self.send_header(k, v)
        self.end_headers()
        self.wfile.write(response.body)
        return True

    def do_GET(self):
        request = BaseHTTPRequestHandler_to_Request(self, 'GET')
        return self.send(self.server._k_webserver.find_and_run_handler(request))

    def do_POST(self):
        request = BaseHTTPRequestHandler_to_Request(self, 'POST', post_params=self.parse_post())
        return self.send(self.server._k_webserver.find_and_run_handler(request))

    def parse_post(self):
        if PY_VER == 2: ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        else: ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
        if PY_VER == 2:
            length = int(self.headers.getheader('content-length'))
        else:
            length = int(self.headers.get('content-length'))
        if ctype == 'multipart/form-data':
            if PY_VER == 3:
                pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                pdict['CONTENT-LENGTH'] = length   # https://bugs.python.org/issue34226 (needed for Py 3.6 on RPi)
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            postvars = parse_qs(self.rfile.read(length), keep_blank_values=1)
            if PY_VER == 2:
                postvars = {k: v[0] for k, v in postvars.items()}
            if PY_VER == 3:
                postvars = {k.decode('utf-8'): v[0].decode('utf-8') for k, v in postvars.items()}
        else: postvars = {}
        return postvars


class WebServer(WebServerBase):
    def __init__(self, *args, **kwargs):
        logging_adapter = kwargs.get('logging_adapter') or LoggingAdapter(
            log_request=C.log_info, log_404=C.log_info,
            log_general=C.log_info, log_exceptions=C.log_error,
            get_logz_html=C.last_logs_html)
        super(WebServer, self).__init__(logging_adapter=logging_adapter, *args, **kwargs)


    def start(self, port=None, listen='0.0.0.0', background=True,
              tls_cert_file=None, tls_key_file=None, tls_key_password=None,
              server_class=DEFAULT_SERVER_CLASS):

        if port: self.port = port         # .start() overrides the constructor.
        if not self.port: self.port = 80

        self.httpd = server_class((listen, self.port), Worker)

        if tls_key_password: raise RuntimeError('TODO: support tls_key_password')
        if tls_key_file:
            self.httpd.socket = ssl.wrap_socket(self.httpd.socket, certfile=tls_cert_file, keyfile=tls_key_file, server_side=True)

        self.httpd._k_webserver = self  # Make my instance visible to handlers.
        self.logger.log_general('starting webserver on port %d' % self.port)
        if background:
            self.web_thread = threading.Thread(target=self.httpd.serve_forever)
            self.web_thread.daemon = True
            self.web_thread.start()
            return self.web_thread
        else:
            self.httpd.serve_forever()
