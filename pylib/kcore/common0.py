'''Common Python helpers: a subset of common.py, which is Circuit Python compatible.

Highlights:
  - Colorizer for console message
  - Simple file in&out w/ exception handling
  - Multi-level logger w/ file/syslog/web output and Circuit Python friendly
  - web getter with exception handling; unifies py2, py3, circuit-py

'''

import os, ssl, sys, time
import kcore.varz as varz

CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
PY_VER = sys.version_info[0]

if not CIRCUITPYTHON:
    import syslog, urllib
    if PY_VER == 2: import urllib2
    else: import urllib.parse, requests


# ----------------------------------------
# colorizers


# CCC = Console Color Codes  :-)
CCC = {
    'black' :   '\033[30m',
    'blue' :    '\033[34m',
    'cyan' :    '\033[36m',
    'green' :   '\033[32m',
    'magenta' : '\033[35m',
    'red' :     '\033[31m',
    'yellow' :  '\033[33m',
    'white' :   '\033[37m',
    'reset' :   '\033[0;0m',
}

def c(msg, color, bold=False):
    '''eg:  print(f"hello {C.c('there', 'green')} world.")'''
    if not sys.stdin.isatty(): return msg
    code = CCC.get(color.lower(), '')
    if bold: code.replace('[', '[1;')
    return code + msg + CCC['reset']


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
    '''Returns contents as a string or list of strings.  filename to "-" for stdin.
       Returns None on error.  list_of_lines + strip will strip all lines.'''
    if wrap_exceptions:
        try:
            if filename == '-':
                data = sys.stdin.read()
            else:
                with open(filename) as f: data = f.read()
        except: return None
    else:
        if filename == '-':
            data = sys.stdin.read()
        else:
            with open(filename) as f: data = f.read()
    if list_of_lines:
        data = data.split('\n')
        if strip: data = [i.strip() for i in data if i != '']
    else:
        if strip: data = data.strip()
    return data


def write_file(filename, data, wrap_exceptions=True):
    '''Write data to a file, or stdout if filename is "-".  Returns True on success.'''
    if filename == '-':
        print(data)
        return True
    if wrap_exceptions:
        try:
            with open(filename, 'w') as f: f.write(data)
        except:
            return False
    else:
        with open(filename, 'w') as f: f.write(data)
    return True


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
    globals()[k] = v


# ---------- Internal state

# In-memory queue of most recent log messages.
LOG_QUEUE = []
LOG_QUEUE_LEN_MAX = 40

# initial state set so that calls to log() will output to stderr BEFORE init_log() is called.
FILTER_LEVEL_LOGFILE = NEVER   # default becomes INFO  once init_log() is called, if not otherwise set.
FILTER_LEVEL_STDOUT = NEVER    # default stays   NEVER once init_log() is called, if not otherwise set.
FILTER_LEVEL_STDERR = INFO     # default becomes ERROR once init_log() is called, if not otherwise set.
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
    if log_queue_len: set_queue_len(log_queue_len)
    if force_time: FORCE_TIME = force_time

    global FILTER_LEVEL_LOGFILE, FILTER_LEVEL_STDOUT, FILTER_LEVEL_STDERR, FILTER_LEVEL_SYSLOG, FILTER_LEVEL_MIN
    FILTER_LEVEL_LOGFILE = filter_level_logfile or INFO
    FILTER_LEVEL_STDOUT = filter_level_stdout or NEVER
    FILTER_LEVEL_STDERR = filter_level_stderr or ERROR
    FILTER_LEVEL_SYSLOG = filter_level_syslog or CRITICAL
    FILTER_LEVEL_MIN = min(FILTER_LEVEL_LOGFILE, FILTER_LEVEL_STDOUT, FILTER_LEVEL_STDERR, FILTER_LEVEL_SYSLOG)

    init_log_tracking(log_title)
    if logfile:
        try:
            if logfile != '-':
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
    time = FORCE_TIME or timestr()
    msg2 = '%s: %s: %s: %s' % (LOG_TITLE, time, level_name, msg)

    # Add to internal in-memory queue
    global LOG_QUEUE, LOG_QUEUE_LEN_MAX
    if LOG_QUEUE_LEN_MAX and len(LOG_QUEUE) >= LOG_QUEUE_LEN_MAX: del LOG_QUEUE[LOG_QUEUE_LEN_MAX - 1]
    LOG_QUEUE.insert(0, msg2)

    # Send to other destinations.
    if level >= FILTER_LEVEL_LOGFILE and LOG_FILENAME:
        msg = '%s:%s:%s: %s' % (level_name, LOG_TITLE, time, msg)
        if LOG_FILENAME == '-': print(msg)
        else:
            with open(LOG_FILENAME, 'a') as f: f.write(msg + '\n')
    if level >= FILTER_LEVEL_STDOUT: print(msg2)
    if level >= FILTER_LEVEL_STDERR: stderr(msg2)
    if level >= FILTER_LEVEL_SYSLOG:
        syslog.syslog(SYSLOG_LEVEL_MAP.get(level, syslog.LOG_INFO), msg2)
        varz.bump('log-sent-syslog')
    return True


def clear_log():
    global LOG_QUEUE
    LOG_QUEUE = []
    if LOG_FILENAME and os.path.exists(LOG_FILENAME): os.unlink(LOG_FILENAME)
    # Clean varz
    rm = []
    for key in varz.VARZ:
        if key.startswith('log-'): rm.append(key)
    for key in rm: varz.VARZ.pop(key)


def set_queue_len(new_len):
    global LOG_QUEUE, LOG_QUEUE_LEN_MAX
    LOG_QUEUE_LEN_MAX = new_len
    if len(LOG_QUEUE) > new_len: LOG_QUEUE = LOG_QUEUE[:new_len]


# Circuit Python doesn't have datetime, so here's our poor-man's-strftime
def timestr():
    now = time.localtime()
    return '%d-%d-%d %d:%d:%d' % (now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)


# Ok, ok, ok, you caught me.  So I did put in a second slightly more subtle
# tracking mechanism.  Fortunately for you, this one also respects the
# $NO_TRACKING environment variable.  Did I forget to mention that you need to
# leave that set all the time, rather than just during make's?  oops.
# I wouldn't dare put in a 3rd even more subtle tracker, would I?  surely not.
TRACKING_DONE = False
def init_log_tracking(log_title):
    if os.environ.get('NO_TRACKING'): return
    global TRACKING_DONE
    if TRACKING_DONE: return
    TRACKING_DONE = True
    d = {'sys': 'ktools', 'ctx': 'log', 'uid': os.getuid(), 'prg': sys.argv[0] }
    read_web('https://point0.net/tracking', timeout=2, get_dict=d, verify_ssl=False)


# ---------- So callers don't need to import logging...


def log_crit(msg):     return log(msg, level=CRITICAL)
def log_crit0cal(msg): return log(msg, level=CRITICAL)
def log_alert(msg):    return log(msg, level=CRITICAL)
def log_error(msg):    return log(msg, level=ERROR)
def log_warning(msg):  return log(msg, level=WARNING)
def log_info(msg):     return log(msg, level=INFO)
def log_debug(msg):    return log(msg, level=DEBUG)


# ----------
# Log queue access passthrough

def last_logs(): return '\n'.join(LOG_QUEUE)
def last_logs_html(): return '<p>' + '<br/>'.join(LOG_QUEUE)


# ----------------------------------------
# web client

# For python3, this is a thin wrapper around requests.  It adds:
# - .exception field with contents of any exception.
# - __str__() method that returns .text

# For python2, installing requests is a pain, so this is provided as a
# partial backport.  See FakeResponse (below) for the emulated fields.


class FakeResponse:
    '''This is a partial emulation of requests.models.Response

       not supported: connection, cookies, encoding, is_redirect,
                      iter_content, iter_lines, json, links, next, history,
                      raise_for_status, request, raw '''

    def __init__(self):
        self.elapsed = None
        self.exception = None
        self.ok = False
        self.headers = {}
        self.status_code = None
        self.text = ''
        self.url = None
    def __str__(self):  return 'ok:%s, code:%s, exception:%s, text:%s, headers:%s, url:%s, elapsed:%s' % (self.ok, self.status_code, self.exception, self.text, self.headers, self.url, self.elapsed)


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


def read_web_e(url, timeout=10, get_dict=None, post_dict=None, verify_ssl=True, wrap_exceptions=True):
    '''Really simple web-get interface; returns a string with either content or human-readable error message.'''
    rslt = web_get(url, timeout, get_dict, post_dict, verify_ssl, wrap_exceptions)
    return rslt.text if rslt.ok else rslt.exception or f'ERROR: [{rslt.status_code}] {rslt.text}'


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
    start_time = time.time()
    res = urllib2.urlopen(req, timeout=timeout, context=ssl_ctx)
    resp = FakeResponse()
    resp.elapsed = time.time() - start_time
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
