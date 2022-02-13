
import cgi, threading, sys
from functools import partial

import k_common

PY_VER = sys.version_info[0]
if PY_VER == 2:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
else:
    from http.server import BaseHTTPRequestHandler, HTTPServer

# Either:
# (1) provide a get_commands_dict, which maps from URL paths (with / prefix) to
# python function calls (which take a single arg, which will be the
# WebHandler instance)
# (2) Dervide a custom subclass from WebHandler and provide a custom do_GET.

# Should work for either Python 2 or 3.
# Uses common for logging and GLOBALS/LOCALS context, which is useful
# for the eval'd functions in the commands_dict.
# (i.e. for #1, you should use common.common_init and provide these)


class WebHandler(BaseHTTPRequestHandler):
    def __init__(self, get_commands_dict={}, context={}, *args, **kwargs):
        self.get_commands = {}
        self.get_prefix_commands = {}
        for i in get_commands_dict:
            if i.endswith('*'):
                self.get_prefix_commands[i[:-1]] = get_commands_dict[i]
            else:
                self.get_commands[i] = get_commands_dict[i]
        self.context = context
        # BaseHTTPRequestHandler calls do_GET **inside** __init__ !!!
        # So we have to call super().__init__ after setting attributes.
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    # common message types: 'text/html' and 'text/plain'.
    def send(self, msg, msg_type='?', code=200):
        if msg_type == '?':
            msg_type = 'text/html' if msg[0] == '<' else 'text'
        self.send_response(code)
        self.send_header("Content-type", msg_type)
        self.end_headers()
        if PY_VER == 3: msg = msg.encode('utf-8')
        self.wfile.write(msg)
        return True

    def do_GET(self):
        if not self.path == '/favicon.ico':
            common.log('recevied web request: %s' % self.path)
        varz_path = self.path.split('?')[0]
        common.varz_bump('web-handler-%s' % varz_path[:14])

        # Try a for a full path match
        out = self._try_cmnd(self.get_commands.get(self.path))
        if out is not None: return out
        # Try for a prefix match
        for i in self.get_prefix_commands:
            if self.path.startswith(i):
                out = self._try_cmnd(self.get_prefix_commands[i])
                if out is not None: return out
        # Standard handlers
        if self.path == '/healthz': return(self.send('ok'))
        elif self.path == '/logz': return(self.send(common.last_logs_html()))
        elif self.path == '/favicon.ico': return
        elif self.path == '/flagz/': return(self.send(common.list_to_csv(common.dict_to_list_of_pairs(vars(common.ARGS))), 'text/plain'))
        elif self.path == '/flagz': return(self.send(common.html_page_wrap(common.list_to_table(common.dict_to_list_of_pairs(vars(common.ARGS))), 'flagz')))
        elif self.path == '/varz/': return(self.send(common.list_to_csv(common.dict_to_list_of_pairs(common.VARZ)), 'text/plain'))
        elif self.path == '/varz': return(self.send(common.html_page_wrap(common.list_to_table(common.dict_to_list_of_pairs(common.VARZ)),'/varz/')))
        # :-(
        common.log('no web handler found')
        self.send('404', code=404)

    def parse_post(self):
        if PY_VER == 2:
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        else:
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            if PY_VER == 2:
                length = int(self.headers.getheader('content-length'))
            else:
                length = int(self.headers.get('content-length'))
            postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
            if PY_VER == 3:
                temp = {}
                for k,v in postvars.items(): temp[k.decode('utf-8')] = v[0].decode('utf-8')
                postvars = temp
        else:
            postvars = {}
        return postvars

    def _try_cmnd(self, cmd):
        if not cmd: return None
        common.log('running cmd: %s' % cmd)
        common.GLOBALS_DICT.update({'self': self})
        # If debuging, don't wrap in a try..except, to get better error message.
        # This has side-effect of disabling prefix command matching.
        if common.DEBUG: return eval(cmd, common.GLOBALS_DICT, common.LOCALS_DICT)
        #
        try:
            return eval(cmd, common.GLOBALS_DICT, common.LOCALS_DICT)
        except Exception as e1:
            try:
                common.log_debug('provided locals dict context failed: %s' % e1)
                common.varz_bump('web-fallback-to-global')
                return eval(cmd, common.GLOBALS_DICT, locals())
            except Exception as e2:
                common.log('cmnd failed [%s]: provided context: %s, local contact: %s' % (cmd, e1, e2))
                common.varz_bump('web-cmnd-failed')
                return None


def start_web_server(port, get_cmnds={}, handler_class=WebHandler, context_dict={}, listen='0.0.0.0', background=True):
    common.log('starting web server')
    common.varz_stamp('web-server-start')

    handler_partial = partial(handler_class, get_cmnds, context_dict)
    httpd = HTTPServer((listen, port), handler_partial)
    if background:
        web_thread = threading.Thread(target=httpd.serve_forever, args=())
        web_thread.daemon = True
        web_thread.start()
        return web_thread
    else:
        httpd.serve_forever()

