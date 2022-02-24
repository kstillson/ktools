
import cgi, threading, sys

import k_common as C           # for logging.
import k_webserver_base as B

PY_VER = sys.version_info[0]
if PY_VER == 2:
    from urlparse import parse_qs
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
else:
    from urllib.parse import parse_qs
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
            if PY_VER == 3:
                pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            if PY_VER == 2:
                length = int(self.headers.getheader('content-length'))
            else:
                length = int(self.headers.get('content-length'))
            postvars = parse_qs(self.rfile.read(length), keep_blank_values=1)
            if PY_VER == 2:
                postvars = {k: v[0] for k, v in postvars.items()}
            if PY_VER == 3:
                postvars = {k.decode('utf-8'): v[0].decode('utf-8') for k, v in postvars.items()}
        else: postvars = {}
        return postvars

    
class WebServer(B.WebServerBase):
    def __init__(self, *args, **kwargs):
        logging_adapter = B.LoggingAdapter(
            log_request=C.log_info, log_404=C.log_info,
            log_general=C.log_info, log_exceptions=C.log_error,
            get_logz_html=C.last_logs_html)
        super(WebServer, self).__init__(logging_adapter=logging_adapter, *args, **kwargs)

    
    def start(self, port=80, listen='0.0.0.0', background=True, server_class=HTTPServer):
        self.httpd = server_class((listen, port), Worker)
        self.httpd._k_webserver = self  # Make my instance visible to handlers.
        self.log_general('starting webserver on port %d' % port)
        if background:
            web_thread = threading.Thread(target=self.httpd.serve_forever)
            web_thread.daemon = True
            web_thread.start()
            return web_thread
        else:
            self.httpd.serve_forever()
