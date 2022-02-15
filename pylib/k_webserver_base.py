
import re
import k_common as C   # for logging
import k_html, k_varz

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
    def __init__(self, body, status_code=200, extra_headers={}, msg_type=None, exception=None):
        self.body = str(body) if body else ''
        self.status_code = status_code
        self.extra_headers = extra_headers
        if self.body:
            self.msg_type = msg_type or ('text/html' if self.body.startswith('<') else 'text')
        else:
            self.msg_type = '?'
        self.exception = exception

    def __str__(self): return '[%d] %s' % (self.status_code, self.body[:70].replace('\n', '\\n'))


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
    def __init__(self, log_request, log_404, log_exceptions, get_logz_html):
        self.log_request = log_request
        self.log_404 = log_404
        self.log_exceptions = log_exceptions
        self.get_logz_html = get_logz_html
        

class WebServerBase(object):
    # TODO: doc
    def __init__(self, handlers={}, context={},
                 wrap_handlers=True, add_default_handlers=True,
                 varz=True, varz_path_trim=14,
                 logging_adapter=None, logging_filters=['favicon.ico'],
                 flagz_args=None):
        self.routes = []
        self.add_handlers(handlers)
        if add_default_handlers: self._add_default_handlers()
        self.context = context
        self.flagz_args = flagz_args
        self.logger = logging_adapter
        self.logging_filters = logging_filters
        self.varz = varz
        self.varz_path_trim = varz_path_trim
        self.wrap_handlers = wrap_handlers
        if varz: k_varz.stamp('web-server-start')


    def add_handlers(self, handlers):
        if isinstance(handlers, dict):
            for k, v in handlers.items(): self.add_handler(k, v)
        else:
            for i in handlers: self.add_handler(i[0], i[1])

    @staticmethod
    def _finalize_regex(route_regex):
        # If route doesn't matches entire path, then add that requirement.
        if not route_regex.startswith('^'): route_regex = '^%s' % route_regex
        if not route_regex.endswith('$'): route_regex = '%s$' % route_regex
        # If route doesn't start with a leading /, add that.
        if not route_regex.startswith('^/'): route_regex = '^/%s' % route_regex[1:]
        return route_regex
            
    def add_handler(self, route_regex, func, fixup_regex=True):
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
            self.logger.log_request('%s: %s' % (request.method, request.full_path))

        # varz
        if self.varz:
            k_varz.bump('web-method-%s' % request.method)
            if self.varz_path_trim:
                trimmed_path = request.full_path[1:(self.varz_path_trim + 1)]
                k_varz.bump('web-path-%s' % trimmed_path)            
        
        # Find a matching handler.
        handler_data = self._find_handler(request.path)
        if not handler_data:
            if self.logger and self.logger.log_404:
                self.logger.log_404('No handler found for: %s' % request.path)
            if self.varz: k_varz.bump('web-status-404')
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
                if self.varz: k_varz.bump('web-handler-exception')
                return Response(None, -1, exception=e)
        else:
            answer = handler_data.func(request)
        
        if not isinstance(answer, Response): answer = Response(answer)
        if self.varz: k_varz.bump('web-status-%d' % answer.status_code)
        return answer

    # Takes a path rather than a pre-built request.  Useful for testing.
    def test_handler(self, path, method='test'):
        return self.find_and_run_handler(Request(method, path))
    

    # ---------- Internals

    def _add_default_handlers(self):
        self.add_handlers([
            ('/favicon.ico',  lambda _: ''),
            ('/flagz',        self._flagz_handler),
            ('/healthz',      lambda _: 'ok'),
            ('/logz',         lambda _: self.logger.get_logz_html()),
            ('/varz',         self._varz_handler),
        ])
        
    def _flagz_handler(self, request):
        if isinstance(self.flagz_args, dict): d= self.flagz_args
        elif self.flagz_args: d= vars(self.flagz_args)
        else: return Response('no flagz data available', 503)  # 503 => "service unavailable"
        return k_html.dict_to_page(d, 'flagz')

    def _varz_handler(self, request):
        if '?' in request.full_path:
            _, var = request.full_path.split('?')
            return str(k_varz.get(var))
        return k_html.dict_to_page(k_varz.VARZ, 'varz')
        
    # returns _HandlerData or None
    def _find_handler(self, path):
        for r in self.routes:
            my_match = r.compiled_regex.match(path)
            if False:  # turn on for debugging...
                sys.stderr.write('ROUTER DEBUG: path %s comp to %s => %s\n' % (path, r.compiled_regex, my_match))
            if my_match:
                r.match_groups = my_match.groups()
                return r            
        return None


# ---------- Other helper functions

# in: full url with get params, out: dict of get params.
def parse_get_params(full_path):
    if '?' not in full_path: return {}
    query_string = full_path.split("?")[1]
    param_list = query_string.split("&")
    params = {}
    for param in param_list:
        if '=' not in param: continue
        key, val = param.split('=')
        params[key] = val    # TODO: decoding...?
    return params


def str_in_substring_list(haystack, list_of_needles):
    for i in list_of_needles:
        if i in haystack: return True
    return False

# circuitpython doesn't have the cgi module, which is used to parse post params.
# so we're going to rely on the caller to provide parsed post params.
def BaseHTTPRequestHandler_to_Request(b, method, post_params={}):
    return Request(method, b.path, headers=b.headers,
                   remote_address=b.headers.get('Host'),
                   post_params=post_params)
