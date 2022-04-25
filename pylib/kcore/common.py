'''Common Python helpers: mostly logging and a web fetcher.

TODO: doc

'''

import datetime, os, ssl, sys
import kcore.log_queue as Q
import kcore.varz as varz

CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
PY_VER = sys.version_info[0]

if not CIRCUITPYTHON:
    import syslog, urllib
    if PY_VER == 2: import urllib2
    else: import urllib.parse, requests


# ----------------------------------------
# Container helpers

def dict_to_list_of_pairs(d):
    return [[key,d[key]] for key in sorted(d)]


def list_to_csv(list_in, field_sep=', ', line_sep='\n'):
    '''Takes a list of lists and outputs lines of csv.
       Works well with the output from dict_to_list_of_pairs().'''
    out = ''
    for i in list_in:
        for j in range(len(i)):
            if not isinstance(j, str): i[j] = str(i[j])
        out += field_sep.join(i)
        out += line_sep
    return out


def str_in_substring_list(haystack, list_of_needles):
    for i in list_of_needles:
        if i in haystack: return True
    return False


# ----------------------------------------
# Simple I/O

def get_input(prompt=""):
    raw_print(prompt)
    return sys.stdin.readline().strip()

def raw_print(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def stderr(msg):
    sys.stderr.write("%s\n" % msg)


def read_file(filename, list_of_lines=False, strip=False, wrap_exceptions=True):
    '''Returns contents as a string or list of strings.
       Returns None on error.  list_of_lines + strip will strip all lines.'''
    if wrap_exceptions:
        try:
            with open(filename) as f: data = f.read()
        except: return None
    else:
        with open(filename) as f: data = f.read()
    if list_of_lines:
        data = data.split('\n')
        if strip: data = [i.strip() for i in data if i != '']
    else:
        if strip: data = data.strip()
    return data


# ----------------------------------------
# logging


# ---------- log level constants

NAME_TO_LEVEL = {
    'ALL':   10,                                             'ALERT': 50,     # custom aliases
    'DEBUG': 10,  'INFO': 20,  'WARNING': 30,  'ERROR': 40,  'CRITICAL': 50,  # standard levels
    'NEVER': 99 }                                                             # custom level

LEVEL_TO_NAME = {v:k for k, v in NAME_TO_LEVEL.items()}        # standard overrides custom.

# Import into module level constants, i.e.  common.INFO will now be available.
for k, v in NAME_TO_LEVEL.items():
    vars()[k] = v


# ---------- Internal state

# initial state set so that calls to log() will output to stderr BEFORE init_log() is called.
FILTER_LEVEL_LOGFILE = NEVER   # default becomes INFO  once init_log() is called, if not otherwise set.
FILTER_LEVEL_STDOUT = NEVER    # default stays   NEVER once init_log() is called, if not otherwise set.
FILTER_LEVEL_STDERR = DEBUG    # default becomes ERROR once init_log() is called, if not otherwise set.
FILTER_LEVEL_SYSLOG = NEVER    # default becomes CRITICAL once init_log() is called, if not otherwise set.
FILTER_LEVEL_MIN = DEBUG

# ---------- Internal state

LOG_FILENAME = None
LOG_TITLE = ''
FORCE_TIME = None

if not CIRCUITPYTHON:
    SYSLOG_LEVEL_MAP = { DEBUG: syslog.LOG_DEBUG, INFO: syslog.LOG_INFO,
                         WARNING: syslog.LOG_WARNING, ERROR: syslog.LOG_ERR,
                         CRITICAL: syslog.LOG_CRIT }


# ---------- business logic

def getLevelName(level): return LEVEL_TO_NAME.get(level)
def getLevelNumber(name): return NAME_TO_LEVEL.get(name)

def init_log(log_title='log', logfile='logfile',
             # The following use the defaults above if no param is provided.
             log_queue_len=None, filter_level_logfile=None,
             filter_level_stdout=None, filter_level_stderr=None, filter_level_syslog=None,
             clear=False,        ## Delete existing logfile and clear internal queue.
             force_time=None):   ## force_time is for testing only.
    if clear: clear_log()

    global LOG_FILENAME, LOG_QUEUE_LEN_MAX, LOG_TITLE, FORCE_TIME
    if log_title: LOG_TITLE = log_title
    if log_queue_len: Q.set_queue_len(log_queue_len)
    if force_time: FORCE_TIME = force_time

    global FILTER_LEVEL_LOGFILE, FILTER_LEVEL_STDOUT, FILTER_LEVEL_STDERR, FILTER_LEVEL_SYSLOG, FILTER_LEVEL_MIN
    FILTER_LEVEL_LOGFILE = filter_level_logfile or INFO
    FILTER_LEVEL_STDOUT = filter_level_stdout or NEVER
    FILTER_LEVEL_STDERR = filter_level_stderr or ERROR
    FILTER_LEVEL_SYSLOG = filter_level_syslog or CRITICAL
    FILTER_LEVEL_MIN = min(FILTER_LEVEL_LOGFILE, FILTER_LEVEL_STDOUT, FILTER_LEVEL_STDERR, FILTER_LEVEL_SYSLOG)

    if logfile:
        try:
            with open(logfile, 'a') as test: pass
            LOG_FILENAME = logfile
        except Exception as e:
            stderr('Error opening primary logfile %s: %s' % (logfile, e))
            try:
                logfile = os.path.basename(logfile)
                with open(logfile, 'a') as test: pass
                LOG_FILENAME = logfile
                stderr('successfully opened fallback local logfile: %s' % LOG_FILENAME)
            except Exception as e:
                LOG_FILENAME = None
                FILTER_LEVEL_STDERR = min(FILTER_LEVEL_STDERR, FILTER_LEVEL_LOGFILE)
                FILTER_LEVEL_LOGFILE = NEVER
                stderr('Also failed to open fallback logfile %s: %s.  Disabling logfile and setting stderr level from standard log level' % (LOG_FILENAME, e))
    varz.set('log-filter-levels', 'file:%s, stdout: %s, stderr: %s, syslog: %s' % (
        getLevelName(FILTER_LEVEL_LOGFILE), getLevelName(FILTER_LEVEL_STDOUT),
        getLevelName(FILTER_LEVEL_STDERR), getLevelName(FILTER_LEVEL_SYSLOG)))
    return True


def log(msg, level=INFO):
    if level < FILTER_LEVEL_MIN: return varz.bump('log-absorbed')
    if level >= ERROR: varz.bump('log-error-or-higher')
    level_name = getLevelName(level)
    time = FORCE_TIME or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg2 = '%s: %s: %s' % (time, level_name, msg)
    msg3 = '%s: %s' % (LOG_TITLE, msg2)
    # Send to various destinations.
    Q.log(msg, level)     # Add to internal queue.
    if level >= FILTER_LEVEL_LOGFILE and LOG_FILENAME:
        with open(LOG_FILENAME, 'a') as f: f.write('%s:%s:%s: %s\n' % (level_name, LOG_TITLE, time, msg))
    if level >= FILTER_LEVEL_STDOUT: print(msg3)
    if level >= FILTER_LEVEL_STDERR: stderr(msg3)
    if level >= FILTER_LEVEL_SYSLOG:
        syslog.syslog(SYSLOG_LEVEL_MAP.get(level, syslog.LOG_INFO), msg2)
        varz.bump('log-sent-syslog')
    return True


def clear_log():
    if LOG_FILENAME and os.path.exists(LOG_FILENAME): os.unlink(LOG_FILENAME)
    Q.clear()
    # Clean varz
    rm = []
    for key in varz.VARZ:
        if key.startswith('log-'): rm.append(key)
    for key in rm: varz.VARZ.pop(key)


# ---------- So callers don't need to import logging...


def log_crit(msg):    log(msg, level=CRITICAL)
def log_alert(msg):   log(msg, level=CRITICAL)
def log_error(msg):   log(msg, level=ERROR)
def log_warning(msg): log(msg, level=WARNING)
def log_info(msg):    log(msg, level=INFO)
def log_debug(msg):   log(msg, level=DEBUG)


# ----------
# Log queue access passthrough

def last_logs(): return Q.last_logs()
def last_logs_html(): return Q.last_logs_html()


# ----------------------------------------
# web client

# For python3, this is a thin wrapper around requests.  It adds:
# - .exception field with contents of any exception.
# - __str__() method that returns .text

# For python2, installing requests is a pain, so this is provided as a
# partial backport.  See FakeResponse (below) for the emulated fields.


class FakeResponse:
    '''This is a partial emulation of requests.models.Response'''
    def __init__(self):
        self.elapsed = None
        self.exception = None
        self.ok = False
        self.headers = {}
        self.status_code = None
        self.text = ''
        self.url = None
    def __str__(self):  return 'ok:%s, code:%s, exception:%s, text:%s, headers:%s, url:%s, elapsed:%s' % (resp.ok, resp.status_code, resp.exception, resp.text, resp.headers, resp.url, resp.elapsed)
        # not supported: connection, cookies, encoding, is_redirect,
        #                iter_content, iter_lines, json, links, next, history,
        #                raise_for_status, request, raw


def web_get(url, timeout=10, get_dict=None, post_dict=None, verify_ssl=True, wrap_exceptions=True, cafile=None, proxy_host=None):
    '''Retrieve web data.  Works for both Python 2 & 3, and hides the differences.

       For Python 3, this is basically a trivial wrapper around "requests",
       mostly just converting annoying byte strings into regular strings.

       For Python 2, this makes an attempt to emulate the requests module.
       Returns a Response-like object.'''
    reader = _read_web2 if PY_VER == 2 else _read_web3
    if wrap_exceptions:
        try:
            return reader(url=url, get_dict=get_dict, post_dict=post_dict,
                          timeout=timeout, verify_ssl=verify_ssl,
                          cafile=cafile, proxy_host=proxy_host)
        except Exception as e:
            r = FakeResponse()
            r.exception = e
            r.url = url
            return r
    else:
        return reader(url=url, get_dict=get_dict, post_dict=post_dict,
                      timeout=timeout, verify_ssl=verify_ssl,
                      cafile=cafile, proxy_host=proxy_host)


def web_get_e(url, *args, **kwargs):
    '''Same as web_get, except will print any exceptions to stderr.'''
    resp = web_get(url, *args, **kwargs)
    if resp.exception: stderr('web_get exception: %s: %s' % (url, resp.exception))
    return resp


def read_web(url, timeout=10, get_dict=None, post_dict=None, verify_ssl=True, wrap_exceptions=True):
    '''Really simple web-get interface; returns a string or None upon error.'''
    return web_get(url, timeout, get_dict, post_dict, verify_ssl, wrap_exceptions).text


# ---------- encoders

# wrappers to auto-determine which version to use...
# "poor man's" versions are for Circuit Python, which doesn't have urllib*

def quote_plus(url):
    if CIRCUITPYTHON: return poor_mans_quote_plus(url)
    elif PY_VER == 2: return urllib.quote_plus(url)
    else: return urllib.parse.quote_plus(url)

    
def unquote_plus(url):
    if CIRCUITPYTHON: return poor_mans_unquote_plus(url)
    elif PY_VER == 2: return urllib.unquote_plus(url)
    else: return urllib.parse.unquote_plus(url)

    
def urlencode(query):
    if CIRCUITPYTHON: return poor_mans_urlencode(query)
    elif PY_VER == 2: return urllib.urlencode(query)
    else: return urllib.parse.urlencode(query)
    

UNQUOTE_REPLACEMENTS = {
    '%20': ' ',    '%22': '"',    '%28': '(',    '%29': ')',
    '%2b': '+',    '%2c': ',',    '%2d': '-',    '%2e': '.',
    '%2f': '/',    '%3a': ':',    '%3d': '=',
    '%5b': '[',    '%5d': ']',    '%5f': '_',
}

def poor_mans_quote_plus(s):
    for repl, srch in UNQUOTE_REPLACEMENTS.items():
        s = s.replace(srch, repl)
    return s

def poor_mans_unquote_plus(s):
    s = s.replace('+', ' ')   # gotta go first...
    for srch, repl in UNQUOTE_REPLACEMENTS.items():
        s = s.replace(srch, repl)
        s = s.replace(srch.upper(), repl)
    return s

def poor_mans_urlencode(query):
    return {poor_mans_quote_plus(k): poor_mans_quote_plus(v) for k, v in query}


# ---------- internals

def _read_web2(url, get_dict=None, post_dict=None, timeout=5, verify_ssl=True, cafile=None, proxy_host=None, extra_headers={}):
    if get_dict:
        data = urlencode(get_dict)
        url += '%s%s' % ('&' if '?' in url else '?', data)
    ssl_ctx = ssl.create_default_context(cafile=cafile)
    if not verify_ssl:
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
    req = urllib2.Request(url, urlencode(post_dict) if post_dict else None, headers=extra_headers)
    if proxy_host:
        req.set_proxy(proxy_host, 'https' if 'https' in url else 'http')
    start_time = datetime.datetime.now()
    res = urllib2.urlopen(req, timeout=timeout, context=ssl_ctx)
    resp = FakeResponse()
    resp.elapsed = datetime.datetime.now() - start_time
    resp.exception = None
    resp.ok = True
    resp.headers = res.headers.dict
    resp.status_code = res.code
    resp.text = res.read()
    resp.url = url
    return resp

def _read_web3(url, get_dict=None, post_dict=None, timeout=5, verify_ssl=True, cafile=None, proxy_host=None, extra_headers={}):
    setattr(requests.models.Response, '__str__', lambda _self: _self.text)
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # nb: only support http-based proxy...
    proxies = { 'http': 'http://%s' % proxy_host } if proxy_host else None
    if get_dict:
        data = urlencode(get_dict)
        url += '%s%s' % ('&' if '?' in url else '?', data)
    if post_dict:
        resp = requests.post(url, data=post_dict, timeout=timeout, verify=cafile if verify_ssl else False, proxies=proxies, headers=extra_headers)
    else:
        resp = requests.get(url, timeout=timeout, verify=cafile if verify_ssl else False, proxies=proxies, headers=extra_headers)
    resp.exception = None
    return resp
