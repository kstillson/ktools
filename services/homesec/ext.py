
# see homesec.py for doc

import subprocess, syslog
import smtplib
from email.mime.text import MIMEText

import kcore.common as C
import kcore.uncommon as UC

# ---------- Global state and controls

DEBUG = False

# ----- rate limiters

RL_CONTROL = UC.RateLimiter(5, 15)
RL_EMAIL =   UC.RateLimiter(4, 30)
RL_PUSH =    UC.RateLimiter(4, 30)
RL_SPEAK =   UC.RateLimiter(4, 30)
RL_SYSLOG =  UC.RateLimiter(10, 20)


# ---------- Silent panic message data

# SITE-SPECIFIC: you should override these values by creating private.d/ext.py
# and putting your site-specific values in there.  See the call to
# UC.load_file_into_module at the bottom for the code that loads this.

SILENT_PANIC_TO = []
SILENT_PANIC_SUBJ = 'URGENT- SILENT PANIC ACTIVATED FOR HOME SECURITY SYSTEM'
SILENT_PANIC_MSG = ('Email message contents...')

DEBUG_SILENT_PANIC_TO = []
DEBUG_SILENT_PANIC_SUBJ = 'THIS IS A TEST - PLEASE IGNORE'
DEBUG_SILENT_PANIC_MSG = SILENT_PANIC_MSG

# ----------

# see ../../tools/etc/speak* for the scripts this service on "pi1" talks to...


def announce(msg, push_level=None, syslog_level=None, details=None, speak=True):
  global RL_SPEAK, RL_SYSLOG
  log_msg = f'announce [{speak=}/{push_level=}/{syslog_level=}]: {msg}'
  if details: log_msg += f': {details}'
  if DEBUG: return C.log_debug(f'ext would announce: {log_msg}')
  C.log(log_msg)
  if speak:
    if RL_SPEAK.check():
      rslt = C.read_web('http://pi1/speak/' + C.quote_plus(msg))
      if not '<p>ok' in rslt: C.log_error(f'unexpected result from speak command: {rslt}')
    else:
      C.log_warning(f'speak request rate limited: {msg}')
  if details: msg += ': %s' % details
  if push_level: push_notification(msg, push_level)
  if syslog_level and RL_SYSLOG.check(): syslog.syslog(syslog_level, msg)


def control(target, command='on'):
  if DEBUG: return C.log_debug(f'ext would control {target} -> {command}')

  global RL_EMAIL
  if not RL_EMAIL.check():
    C.log_warning(f'rate limited control {target=} {command=}')
    return 'ERROR: rate limited'

  out = C.read_web(f'https://home.point0.net/control/{target}/{command}')
  if 'ok' in out:
    C.log(f'sent control command {target} -> {command}')
    return None
  C.log_error(f'error sending control {target} -> {command}: {out}')
  return out


# put here so easier to mock out during testing.
def read_web(url):
  if DEBUG:
    C.log_debug(f'ext would read_web: {url}')
    return 'ok: debug mode; read-web skipped'
  return C.read_web(url)


# levels supported by client-side: alert, info, other
def push_notification(msg, level='other'):
  if DEBUG: return C.log_debug(f'ext would push notification {msg}@{level}')

  global RL_PUSH
  if not RL_PUSH.check():
    C.log_warning(f'rate limited push notification: [level={level}: {msg}')
    return -2

  C.log(f'pushbullet sending [level={level}]: {msg}')
  if level != 'other': msg += ' !%s' % level
  ok = subprocess.call(["/usr/local/bin/pb-push", msg])
  if ok != 0: C.log_warning(f'pushbullet returned unexpected status {ok}')
  return ok == 0


def send_emails(from_addr, to, subj, contents):
  if DEBUG: return C.log_debug(f'ext would send email {to=} {subj=}')

  global RL_EMAIL
  if not RL_EMAIL.check():
    C.log_warning(f'rate limited email {to=} {subj=}')
    return

  msg = MIMEText(contents)
  msg['Subject'] = subj
  msg['From'] = from_addr
  msg['To'] = ', '.join(to)
  s = smtplib.SMTP('exim4.h.point0.net')
  s.sendmail(from_addr, to, msg.as_string())
  s.quit()


def send_email(from_addr, to, subj, contents):
  return send_emails(from_addr, [to], subj, contents)


def silent_panic():
  if DEBUG: return C.log_debug(f'ext would run silent panic routine')
  C.log_crit('SILENT PANIC ACTIVATED!')
  send_emails('ken@kenstillson.com',
              DEBUG_SILENT_PANIC_TO if DEBUG else SILENT_PANIC_TO,
              DEBUG_SILENT_PANIC_SUBJ if DEBUG else SILENT_PANIC_SUBJ,
              DEBUG_SILENT_PANIC_MSG if DEBUG else SILENT_PANIC_MSG)


# ---------- private.d overrides

UC.load_file_into_module('private.d/ext.py')
