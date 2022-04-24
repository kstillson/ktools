'''TODO: doc

TODO: add support for basic auth (with db file compatible with htpasswd...?)
'''

import re, os, sys
import kcore.html, kcore.varz

CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
PY_VER = sys.version_info[0]

if not CIRCUITPYTHON:   # urllib not currently available in circuitpy
    if PY_VER == 2: import urllib
    else: import urllib.parse

# A populated instance of this class is passed to handlers.
class Request:
    def __init__(self, method, full_path,
                 body=None, context={}, headers={}, post_params={}, remote_address=None, route_match_groups={}):
        self.body = body
        self.context = context        # See WebServerBase constructor.
        self.full_path = full_path
        self.headers = headers
        self.method = method
        self.get_params = parse_get_params(full_path)
        self.path = full_path.split("?")[0]
        self.post_params = post_params
        self.remote_address = remote_address
        self.route_match_groups = route_match_groups

    def __str__(self): return self.path


# Handlers may return a populated instance of this class, or just
# a string if they're happy with status 200 and default headers.
#
# .exception: If processing generates an exception, a handler may populate
# this to communicate up the stack (eventually causing a status 500 reply).
# If the web-server has wrap_handlers turned on, it does this for you.
class Response:
    def __init__(self, body, status_code=200, extra_headers={}, msg_type=None, exception=None, status_msg=None, binary=False):
        if binary: self.body = body
        else: self.body = str(body) if body else ''
        self.status_code = status_code
        self.ok = (status_code == 200)
        self.status_msg = 'OK' if status_code == 200 else 'NOTOK'
        self.extra_headers = extra_headers
        if msg_type:
            self.msg_type = msg_type
        else:
            if self.body:
                self.msg_type = msg_type or ('text/html' if self.body.startswith('<') else 'text')
            else:
                self.msg_type = '?'
        self.exception = exception
        self.binary = binary

    def __str__(self): return '[%d] %s' % (self.status_code, self.exception or self.body[:70].replace('\n', '\\n'))


# Internal use class for tracking handlers.
class _HandlerData:
    def __init__(self, regex, func):
        self.regex = regex
        self.compiled_regex = re.compile(regex)
        self.func = func
        self.match_groups = None   # Populated once match is made.


# WebServerBase expects an instance of this as logging_adapter.
# This is taken care of by the subclasses of WebServerBase.
class LoggingAdapter:
    def __init__(self, log_request, log_404, log_general, log_exceptions, get_logz_html):
        self.log_request = log_request
        self.log_404 = log_404
        self.log_general = log_general
        self.log_exceptions = log_exceptions
        self.get_logz_html = get_logz_html


class WebServerBase(object):
    # TODO: doc

    # TODO: allow passing port to constructor OR start method.

    # Note: caller-provided handlers always take presidence over the built-in
    # "standard" handlers, unless a handler with a route_regex of None is
    # added, in which case it automatically becomes the "fallback" or "defaul"
    # handler, which is always matched if nothing else matches.  If you want a
    # default handler which overrides the standard handlers, either turn them
    # off via use_standard_handlers=False in the constructor, or add a handler
    # with the route ".*".

    def __init__(self, handlers={}, context={},
                 wrap_handlers=True, use_standard_handlers=True,
                 varz=True, varz_path_trim=14,
                 logging_adapter=None, logging_filters=['favicon.ico'],
                 flagz_args=None):
        self.routes = []
        self.default_handler = None
        self.add_handlers(handlers)
        self.context = context
        self.flagz_args = flagz_args
        self.logger = logging_adapter
        self.logging_filters = logging_filters
        self.varz = varz
        self.varz_path_trim = varz_path_trim
        self.wrap_handlers = wrap_handlers
        if varz: kcore.varz.stamp('web-server-start')
        if use_standard_handlers:
            self.standard_handlers = {
                '/favicon.ico':  lambda _: '',
                '/flagz':        lambda request: self._flagz_handler(request),
                '/healthz':      lambda _: 'ok',
                '/logz':         lambda _: self.logger.get_logz_html(),
                '/varz':         lambda request: varz_handler(request),
            }
        else: self.standard_handlers = {}


    def add_handlers(self, handlers):
        if not handlers: return
        if isinstance(handlers, dict):
            for k, v in handlers.items(): self.add_handler(k, v)
        else:
            for i in handlers: self.add_handler(i[0], i[1])

    @staticmethod
    def _finalize_regex(route_regex):
        # Make sure pattern matches entire path.
        if not route_regex.startswith('^'): route_regex = '^%s' % route_regex
        if not route_regex.endswith('$'): route_regex = '%s$' % route_regex
        # If route doesn't start with a leading /, add that.
        if not route_regex.startswith('^/'): route_regex = '^/' + route_regex[1:]
        return route_regex

    def add_handler(self, route_regex, func, fixup_regex=True):
        if not route_regex:
            self.default_handler = func
            return
        if fixup_regex: route_regex = WebServerBase._finalize_regex(route_regex)
        self.routes.append(_HandlerData(route_regex, func))

    def del_handler(self, route_regex):
        fixed_regex = WebServerBase._finalize_regex(route_regex)
        for i, r in enumerate(self.routes):
            if r.regex == fixed_regex:
                self.routes.pop(i)
                return True
        return False

    # Takes a Request, returns a populated Response.
    def find_and_run_handler(self, request):
        # Logging
        if (self.logger
            and self.logger.log_request
            and not str_in_substring_list(request.full_path, self.logging_filters)):
            # Get params can be sensitive, so log path rather than full_path.
            self.logger.log_request('%s: %s' % (request.method, request.path))

        # varz
        if self.varz:
            kcore.varz.bump('web-method-%s' % request.method)
            if self.varz_path_trim:
                trimmed_path = request.full_path[1:(self.varz_path_trim + 1)]
                kcore.varz.bump('web-path-%s' % trimmed_path)

        # Find a matching handler.
        handler_data = self._find_handler(request.path)
        if not handler_data:
            if self.logger and self.logger.log_404:
                self.logger.log_404('No handler found for: %s' % request.path)
            if self.varz: kcore.varz.bump('web-status-404')
            return Response('page not found', 404)

        # Finalize request instance contents.
        request.context = self.context
        request.route_match_groups = handler_data.match_groups

        # And call the handler.
        if self.wrap_handlers:
            try:
                answer = handler_data.func(request)
            except Exception as e:
                if self.logger and self.logger.log_exceptions:
                    self.logger.log_exceptions('handler exception. path=%s, error=%s' % (request.path, e))
                if self.varz: kcore.varz.bump('web-handler-exception')
                return Response(None, -1, exception=e)
        else:
            answer = handler_data.func(request)

        if isinstance(answer, int):   answer = Response(str(answer))
        if isinstance(answer, float): answer = Response(str(answer))
        if isinstance(answer, str):   answer = Response(answer)
        if self.varz: kcore.varz.bump('web-status-%d' % answer.status_code)
        return answer

    # Takes a path rather than a pre-built request.  Useful for testing.
    def test_handler(self, path, method='test'):
        return self.find_and_run_handler(Request(method, path))


    # ---------- Internals

    def _flagz_handler(self, request):
        if isinstance(self.flagz_args, dict): d= self.flagz_args
        elif self.flagz_args: d= vars(self.flagz_args)
        else: return Response('no flagz data available', 503)  # 503 => "service unavailable"
        return kcore.html.dict_to_page(d, 'flagz')

    # returns _HandlerData or None
    def _find_handler(self, path):
        for r in self.routes:
            my_match = r.compiled_regex.match(path)
            if False:  # turn on for debugging...
                sys.stderr.write('ROUTER DEBUG: path %s comp to %s => %s\n' % (path, r.compiled_regex, my_match))
            if my_match:
                r.match_groups = my_match.groups()
                return r
        # Check for a standard handler match.
        stnd = self.standard_handlers.get(path)
        if stnd: return _HandlerData(path, stnd)
        # Check for a default handler.
        if self.default_handler: return _HandlerData(path, self.default_handler)
        # No handler found.
        return None


# ---------- Other helper functions

def varz_handler(request, extra_dict=None):
    if extra_dict:
        varz = dict(kcore.varz.VARZ)
        varz.update(extra_dict)
    else:
        varz = kcore.varz.VARZ
    if '?' in request.full_path:
        _, var = request.full_path.split('?')
        return str(varz.get(var))
    return kcore.html.dict_to_page(varz, 'varz')


REPLACEMENTS = {
    '%20': ' ',    '%22': '"',    '%28': '(',    '%29': ')',
    '%2b': '+',    '%2c': ',',    '%2d': '-',    '%2e': '.',
    '%2f': '/',    '%3a': ':',    '%3d': '=',
    '%5b': '[',    '%5d': ']',    '%5f': '_',
}
def poor_mans_unquote(s):
    s = s.replace('+', ' ')   # gotta go first...
    for srch, repl in REPLACEMENTS.items():
        s = s.replace(srch, repl)
        s = s.replace(srch.upper(), repl)
    return s


# in: full url with get params, out: dict of get params.
def parse_get_params(full_path):
    if '?' not in full_path: return {}
    query_string = full_path.split("?")[1]
    param_list = query_string.split("&")
    params = {}
    for param in param_list:
        if '=' not in param: continue
        key, val = param.split('=')
        if CIRCUITPYTHON:
            # urllib not available; let's make a few basic fixes manually and hope for the best.
            key = poor_mans_unquote(key)
            val = poor_mans_unquote(val)
        elif PY_VER == 2:
            key = urllib.unquote(key)
            val = urllib.unquote(val)
        else:
            key = urllib.parse.unquote(key)
            val = urllib.parse.unquote(val)
        params[key] = val
    return params


def str_in_substring_list(haystack, list_of_needles):
    for i in list_of_needles:
        if i in haystack: return True
    return False

# circuitpython doesn't have the cgi module, which is used to parse post params.
# so we're going to rely on the caller to provide parsed post params.
def BaseHTTPRequestHandler_to_Request(b, method, post_params={}):
    return Request(method, b.path, headers=b.headers,
                   remote_address=b.client_address[0],
                   post_params=post_params)
