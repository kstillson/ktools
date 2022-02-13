
import contextlib, datetime, logging, grp, os, pwd, syslog, time, urllib, ssl, sys
import k_varz as varz

PY_VER = sys.version_info[0]
if PY_VER == 2:
    import StringIO as io
    import urllib2
else:
    import io, urllib.parse, urllib.request


# ----------------------------------------
# Container helpers

def dict_to_list_of_pairs(d):
    out = []
    for i in sorted(d):
        out.append([i, d[i]])
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

'''Temporarily captures stdout and stderr and makes them available.
Example usage:
  with k_common.Capture() as cap:
    # (write stuff to stdout and/or stderr...)
    caught_stdout = cap.out
    caught_stderr = cap.err
  # (do stuff with caught_stdout, caught_stderr...)
'''
class Capture():
    def __enter__(self):
        self._real_stdout = sys.stdout
        self._real_stderr = sys.stderr
        self.stdout = sys.stdout = io.StringIO()
        self.stderr = sys.stderr = io.StringIO()
        return self
    def __exit__(self, type, value, traceback):
        sys.stdout = self._real_stdout
        sys.stderr = self._real_stderr
    @property
    def out(self): return self.stdout.getvalue()
    @property
    def err(self): return self.stderr.getvalue()


# ----------------------------------------
# File I/O

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
# System interaction

def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    if os.getuid() != 0: return
    running_uid = pwd.getpwnam(uid_name).pw_uid
    running_gid = grp.getgrnam(gid_name).gr_gid
    os.setgroups([])
    os.setgid(running_gid)
    os.setuid(running_uid)
    old_umask = os.umask(0o077)


# Run a string as Python code, returns any stdout as a string, or False on failure.
def exec_wrapper(cmd, locals=globals()):
    old_stdout = sys.stdout
    new_stdout = sys.stdout = io.StringIO()
    try:
        exec(cmd, globals(), locals)
        return new_stdout.getvalue().strip()
    except Exception as e:
        sys.stdout = old_stdout  # in-case logger wants to print...
        log_error('exception during exec: %s : %s' % (cmd, e))
        return False
    finally:
        sys.stdout = old_stdout


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
LOG_QUEUE = []
LOG_QUEUE_LEN_MAX = 20
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
    if log_queue_len: LOG_QUEUE_LEN_MAX = log_queue_len
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
    global LOG_QUEUE
    if LOG_QUEUE_LEN_MAX and len(LOG_QUEUE) > LOG_QUEUE_LEN_MAX: del LOG_QUEUE[LOG_QUEUE_LEN_MAX]
    LOG_QUEUE.insert(0, msg2)
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
    global LOG_QUEUE, LOG_INIT_DONE
    LOG_QUEUE = []
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
# Log queue access

def last_logs(): return '\n'.join(LOG_QUEUE)
def last_logs_html(): return '<p>' + '<br/>'.join(LOG_QUEUE)


# ----------------------------------------
# web client

def read_web(url, timeout=10,
             get_dict=None, post_dict=None,
             verify_ssl=True, wrap_exceptions=True):
    reader = _read_web2 if PY_VER == 2 else _read_web3
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    if wrap_exceptions:
        try:
            return reader(url, get_dict, post_dict, timeout, ctx)
        except Exception as e:
            log_error('error getting URL: %s: %s' % (url, e))
            return None
    else:
        return reader(url, get_dict, post_dict, timeout, ctx)


# ---------- other web client helper functions

def quote_plus(url):
    return urllib.quote_plus(url) if PY_VER == 2 else urllib.parse.quote_plus(url)

def read_web_noverify(url, timeout=5):
    return read_web(url, timeout, verify_ssl=False)


# ---------- internals

def _read_web2(url, get_dict=None, post_dict=None, timeout=5, ctx=None):
    if get_dict:
        data = urllib.urlencode(get_dict)
        url += '%s%s' % ('&' if '?' in url else '?', data)
    req = urllib2.Request(url, urllib.urlencode(post_dict) if post_dict else None)
    return urllib2.urlopen(req, timeout=timeout, context=ctx).read()

def _read_web3(url, get_dict=None, post_dict=None, timeout=5, ctx=None):
    if get_dict:
        data = urllib.parse.urlencode(get_dict, quote_via=urllib.parse.quote_plus)
        url += '%s%s' % ('&' if '?' in url else '?', data)
    data = urllib.parse.urlencode(post_dict).encode() if post_dict else None
    with urllib.request.urlopen(url, data=data, timeout=timeout, context=ctx) as resp:
        return resp.read().decode('utf-8')



