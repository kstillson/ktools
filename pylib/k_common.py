
import datetime, logging, os, syslog, time, urllib, ssl, sys
import k_log_queue as Q
import k_varz as varz

PY_VER = sys.version_info[0]
if PY_VER == 2: import urllib2
else: import urllib.parse, requests


# ----------------------------------------
# Container helpers

def dict_to_list_of_pairs(d):
    out = []
    for i in sorted(d): out.append([i, d[i]])
    return out


# Actually takes a list of lists and output lines of csv.
# (Designed to take the output of dict_to_list_of_pairs())
def list_to_csv(list_in, field_sep=', ', line_sep='\n'):
    out = ''
    for i in list_in:
        for j in range(len(i)):
            if not isinstance(j, str): i[j] = str(i[j])
        out += field_sep.join(i)
        out += line_sep
    return out


# ----------------------------------------
# I/O

def get_input(prompt=""):
    raw_print(prompt)
    return sys.stdin.readline().strip()

def raw_print(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def stderr(msg):
    sys.stderr.write("%s\n" % msg)


# Returns contents as string or list of strings (as-per list_of_lines), and
# returns None on error.  list_of_lines + strip will strip all lines.
def read_file(filename, list_of_lines=False, strip=False, wrap_exceptions=True):
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
# logging abstraction

logging.NEVER = 99

# Internal state, and defaults if not overriden by calling init_log().
FILTER_LEVEL_LOGFILE = logging.INFO
FILTER_LEVEL_STDOUT = logging.NEVER
FILTER_LEVEL_STDERR = logging.ERROR
FILTER_LEVEL_SYSLOG = logging.CRITICAL
FILTER_LEVEL_MIN = min(FILTER_LEVEL_LOGFILE, FILTER_LEVEL_STDOUT, FILTER_LEVEL_STDERR, FILTER_LEVEL_SYSLOG)

# Internal state
LOGGER = None
LOG_FILENAME = None
LOG_TITLE = ''
LOG_INIT_DONE = False
FORCE_TIME = None

SYSLOG_LEVEL_MAP = { logging.DEBUG: syslog.LOG_DEBUG, logging.INFO: syslog.LOG_INFO,
                     logging.WARNING: syslog.LOG_WARNING, logging.ERROR: syslog.LOG_ERR,
                     logging.CRITICAL: syslog.LOG_CRIT }

# ----------

def init_log(log_title='log', logfile='logfile',
             # The following use the defaults above if no param is provided.
             log_queue_len=None, filter_level_logfile=None,
             filter_level_stdout=None, filter_level_stderr=None, filter_level_syslog=None,
             clear=False,        ## Delete existing logfile and clear internal queue.
             force_time=None):   ## force_time is for testing only.
    if clear: clear_log()

    global LOGGER, LOG_INIT_DONE, LOG_QUEUE_LEN_MAX, LOG_TITLE, FORCE_TIME
    LOG_INIT_DONE = True  # Start with this so any other threads yield to this one.
    if log_title: LOG_TITLE = log_title
    if log_queue_len: Q.set_queue_len(log_queue_len)
    if force_time: FORCE_TIME = force_time

    global FILTER_LEVEL_LOGFILE, FILTER_LEVEL_STDOUT, FILTER_LEVEL_STDERR, FILTER_LEVEL_SYSLOG, FILTER_LEVEL_MIN
    if filter_level_logfile: FILTER_LEVEL_LOGFILE = filter_level_logfile
    if filter_level_stdout: FILTER_LEVEL_STDOUT = filter_level_stdout
    if filter_level_stderr: FILTER_LEVEL_STDERR = filter_level_stderr
    if filter_level_syslog: FILTER_LEVEL_SYSLOG = filter_level_syslog
    FILTER_LEVEL_MIN = min(FILTER_LEVEL_LOGFILE, FILTER_LEVEL_STDOUT, FILTER_LEVEL_STDERR, FILTER_LEVEL_SYSLOG)

    if not logfile:
        LOGGER = None
        return True
    global LOG_FILENAME
    try:
        LOG_FILENAME = logfile
        logging.basicConfig(filename=LOG_FILENAME, level=filter_level_logfile, filemode='a', force=True)
    except Exception as e:
        stderr('Error opening primary logfile %s: %s' % (logfile, e))
        try:
            LOG_FILENAME = os.path.basename(logfile)
            logging.basicConfig(filename=LOG_FILENAME, level=filter_level_logfile, filemode='a', force=True)
            stderr('successfully opened fallback local logfile: %s' % LOG_FILENAME)
        except Exception as e:
            LOG_FILENAME = None
            print('Also failed to open fallback logfile %s: %s.  Disabling logfile.' % (LOG_FILENAME, e))
            return False
    LOGGER = logging.getLogger(log_title or 'log')
    LOGGER.setLevel(FILTER_LEVEL_LOGFILE)
    varz.set('log-filter-levels', 'file:%s, stdout: %s, stderr: %s, syslog%s' % (
        logging.getLevelName(FILTER_LEVEL_LOGFILE), logging.getLevelName(FILTER_LEVEL_STDOUT),
        logging.getLevelName(FILTER_LEVEL_STDERR), logging.getLevelName(FILTER_LEVEL_SYSLOG)))
    return True


def log(msg, level=logging.INFO):
    if not LOG_INIT_DONE: init_log()
    if level < FILTER_LEVEL_MIN: return varz.bump('log-absorbed')
    if level >= logging.ERROR: varz.bump('log-error-or-higher')
    level_name = logging.getLevelName(level)
    title = '%s: ' % LOG_TITLE if LOG_TITLE else ''
    time = FORCE_TIME or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg1 = '%s: %s' % (time, msg)
    msg2 = '%s: %s' % (level_name, msg1)
    # Add to internal queue.
    Q.log(msg, level)
    # Send to various destinations.
    if level >= FILTER_LEVEL_LOGFILE and LOGGER: LOGGER.log(level, msg1)
    if level >= FILTER_LEVEL_STDOUT: print(title + msg2)
    if level >= FILTER_LEVEL_STDERR: stderr(title + msg2)
    if level >= FILTER_LEVEL_SYSLOG:
        syslog.syslog(SYSLOG_LEVEL_MAP.get(level, syslog.LOG_INFO), msg2)
        varz.bump('log-sent-syslog')
    return True


def clear_log():
    if LOG_FILENAME and os.path.exists(LOG_FILENAME): os.unlink(LOG_FILENAME)
    global LOG_INIT_DONE
    Q.clear()
    LOG_INIT_DONE = False
    # Clean varz
    rm = []
    for key in varz.VARZ:
        if key.startswith('log-'): rm.append(key)
    for key in rm: varz.VARZ.pop(key)
    # Remove all handlers associated with the root logger object.
    # (needed for python2 to recover from calling basicConfig multiple times.)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)


# ---------- So callers don't need to import logging...

def log_crit(msg): log(msg, level=logging.CRITICAL)
def log_alert(msg): log(msg, level=logging.CRITICAL)

def log_error(msg): log(msg, level=logging.ERROR)

def log_warning(msg): log(msg, level=logging.WARNING)

def log_info(msg): log(msg, level=logging.INFO)

def log_debug(msg): log(msg, level=logging.DEBUG)


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

# This is a partial emulation of requests.models.Response
class FakeResponse:
    def __init__(self):
        self.elapsed = None
        self.exception = None
        self.ok = False
        self.headers = {}
        self.status_code = None
        self.text = ''
        self.url = None
    def __str__(self): return self.text
        # not supported: connection, cookies, encoding, is_redirect,
        #                iter_content, iter_lines, json, links, next, history,
        #                raise_for_status, request, raw

# For python2, this emulates the python3 requests framework.  i.e. the caller
# can use web_get to provide the same API regardless of Python version.

def web_get(url, timeout=10, get_dict=None, post_dict=None, verify_ssl=True, wrap_exceptions=True):
    reader = _read_web2 if PY_VER == 2 else _read_web3
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    if wrap_exceptions:
        try:
            return reader(url, get_dict, post_dict, timeout, verify_ssl)
        except Exception as e:
            r = FakeResponse()
            r.exception = e
            r.url = url
            return r
    else:
        return reader(url, get_dict, post_dict, timeout, verify_ssl)

# For a really simple interface: returns a string or None upon error.
def read_web(url, timeout=10, get_dict=None, post_dict=None, verify_ssl=True, wrap_exceptions=True):
    return web_get(url, timeout, get_dict, post_dict, verify_ssl, wrap_exceptions).text


def read_web_noverify(url, timeout=10, get_dict=None, post_dict=None, wrap_exceptions=True):
    return read_web(url, timeout, get_dict, post_dict, False, wrap_exceptions)


# ---------- other web client helper functions

def quote_plus(url):
    if PY_VER == 2: return urllib.quote_plus(url)
    else: urllib.parse.quote_plus(url)


# ---------- internals

def _read_web2(url, get_dict=None, post_dict=None, timeout=5, verify_ssl=True):
    if get_dict:
        data = urllib.urlencode(get_dict)
        url += '%s%s' % ('&' if '?' in url else '?', data)
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib2.Request(url, urllib.urlencode(post_dict) if post_dict else None)
    start_time = datetime.datetime.now()
    res = urllib2.urlopen(req, timeout=timeout, context=ctx)
    resp = FakeResponse()
    resp.elapsed = datetime.datetime.now() - start_time
    resp.exception = None
    resp.ok = True
    resp.headers = res.headers.dict
    resp.status_code = res.code
    resp.text = res.read()
    resp.url = url
    return resp

def _read_web3(url, get_dict=None, post_dict=None, timeout=5, verify_ssl=True):
    setattr(requests.models.Response, '__str__', lambda _self: _self.text)
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if get_dict:
        data = urllib.parse.urlencode(get_dict, quote_via=urllib.parse.quote_plus)
        url += '%s%s' % ('&' if '?' in url else '?', data)
    if post_dict:
        resp = requests.post(url, data=post_dict, timeout=timeout, verify=None if verify_ssl else False)
    else:
        resp = requests.get(url, timeout=timeout, verify=None if verify_ssl else False)
    resp.exception = None
    return resp
