
import cgi, threading, sys
from functools import partial

import k_webserver_base as B

PY_VER = sys.version_info[0]
if PY_VER == 2:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
else:
    from http.server import BaseHTTPRequestHandler, HTTPServer


class Worker(BaseHTTPRequestHandler):

    def send(self, response):
        if not response.msg_type:
            response.msg_type = 'text/html' if response.body.startswith('<') else 'text'
        self.send_response(response.status_code)
        self.send_header("Content-type", response.msg_type)
        for k, v in response.extra_headers.items(): self.send_header(k, v)
        self.end_headers()
        if PY_VER == 3: response.body = response.body.encode('utf-8')
        self.wfile.write(response.body)
        return True
        
    def do_GET(self):
        request = B.BaseHTTPRequestHandler_to_Request(self, 'GET')
        return self.send(self.server._k_webserver.find_and_run_handler(request))

    def do_POST(self):
        request = B.BaseHTTPRequestHandler_to_Request(self, 'POST', post_params=self.parse_post())
        return self.send(self.server._k_webserver.find_and_run_handler(request))
        
    def parse_post(self):
        if PY_VER == 2: ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        else: ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            if PY_VER == 2: length = int(self.headers.getheader('content-length'))
            else: length = int(self.headers.get('content-length'))
            postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
            if PY_VER == 3:
                temp = {}
                for k,v in postvars.items(): temp[k.decode('utf-8')] = v[0].decode('utf-8')
                postvars = temp
        else: postvars = {}
        return postvars

    
class WebServer(B.WebServerBase):
    # args & kwargs are passed along to WebServerBase's constructor.
    def __init__(self, *args, **kwargs):
        if PY_VER == 2: super(WebServer, self).__init__(*args, **kwargs)
        else: super().__init__(*args, **kwargs)

    # args & kwargs are passed along to BaseHTTPRequestHandler's constructor.
    def start(self, port=80, listen='0.0.0.0', background=True, *args, **kwargs):
        self.httpd = HTTPServer((listen, port), Worker)
        self.httpd._k_webserver = self  # Make my instance visible to handlers.
        if background:
            web_thread = threading.Thread(target=self.httpd.serve_forever)
            web_thread.daemon = True
            web_thread.start()
            return web_thread
        else:
            self.httpd.serve_forever()
