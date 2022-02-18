
from k_common_base import *

import os, ssl, sys
import k_log_queue as Q
import k_varz as varz

from k_log_queue import Levels, LEVELS


# ----------
# Are we running CircuitPython? If not, inject path to the simulator.
CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')  # TODO: any better way?
if not CIRCUITPYTHON: sys.path.insert(0, 'circuitpy_sim')
# ----------

import adafruit_requests as R


# ----------------------------------------
# logging abstraction

# Internal state
FILTER_LEVEL_QUEUE = LEVELS.NEVER
FILTER_LEVEL_SERIAL = LEVELS.NEVER


def init_log(filter_level_queue=LEVELS.INFO, filter_level_serial=LEVELS.INFO,
             log_queue_len=50,
             clear=False,        ## Delete existing queue?
             force_time=None):   ## force_time is for testing only.
    FILTER_LEVEL_QUEUE = filter_level_queue
    FILTER_LEVEL_SERIAL = filter_level_serial
    if log_queue_len: Q.set_queue_len(log_queue_len)
    if clear: Q.clear_log()
    Q.FORCE_TIME = force_time
    varz.set('log-filter-levels', 'queue:%s, serial: %s' % (
        Levels.name(filter_level_queue), Levels.name(filter_level_serial)))
    return True


def log(msg, level=LEVELS.INFO):
    if level >= FILTER_LEVEL_QUEUE: Q.log(msg, level)
    if level >= FILTER_LEVEL_SERIAL: print(Q.decorate_msg(msg, level))
    if level >= LEVELS.ERROR: varz.bump('log-error-or-higher')
    return True


def clear_log():
    Q.clear()
    LOG_INIT_DONE = False
    # Clean varz
    rm = []
    for key in varz.VARZ:
        if key.startswith('log-'): rm.append(key)
    for key in rm: varz.VARZ.pop(key)


# ---------- So callers don't need to import logging...

def log_crit(msg): log(msg, level=LEVEL.CRITICAL)
def log_alert(msg): log(msg, level=LEVEL.CRITICAL)
def log_error(msg): log(msg, level=LEVEL.ERROR)
def log_warning(msg): log(msg, level=LEVEL.WARNING)
def log_info(msg): log(msg, level=LEVEL.INFO)
def log_debug(msg): log(msg, level=LEVEL.DEBUG)


# ----------
# Log queue access passthrough

def last_logs(): return Q.last_logs()
def last_logs_html(): return Q.last_logs_html()


# ----------------------------------------
# web client

# This wrapper tries to make adafruit_requests look more like Python3 requests.

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

    
def web_get(url, timeout=10, get_dict=None, post_dict=None, verify_ssl=True, wrap_exceptions=True):
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    if wrap_exceptions:
        try:
            return _read_web3(url, get_dict, post_dict, timeout, verify_ssl)
        except Exception as e:
            r = FakeResponse()
            r.exception = e
            r.url = url
            return r
    else:
        return _read_web3(url, get_dict, post_dict, timeout, verify_ssl)

# For a really simple interface: returns a string or None upon error.
def read_web(url, timeout=10, get_dict=None, post_dict=None, verify_ssl=True, wrap_exceptions=True):
    return web_get(url, timeout, get_dict, post_dict, verify_ssl, wrap_exceptions).text


def read_web_noverify(url, timeout=10, get_dict=None, post_dict=None, wrap_exceptions=True):
    return read_web(url, timeout, get_dict, post_dict, False, wrap_exceptions)


# ---------- internals

def _read_web3(url, get_dict=None, post_dict=None, timeout=5, verify_ssl=True):
    if get_dict:
        # TODO: add url encoding.
        url += '?' + '&'.join(['%s=%s' % (key, value) for key, value in get_dict.items()])
    if post_dict:
        resp = R.post(url, data=post_dict, timeout=timeout, verify=None if verify_ssl else False)
    else:
        resp = R.get(url, timeout=timeout, verify=None if verify_ssl else False)
    resp.__str__ = lambda _self: _self.text
    resp.exception = None
    return resp
