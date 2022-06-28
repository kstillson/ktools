
import subprocess, syslog
import smtplib
from email.mime.text import MIMEText

import kcore.common as C

DEBUG = False


# --------------------
# Silent alarm message data

# TODO: move to addrs into private.d

SILENT_TO = ['rts@point0.net', 'mbs@point0.net']
SILENT_SUBJ = 'URGENT- KEN STILLSON HAS ACTIVATED HOME SECURITY PANIC SYSTEM'
SILENT_MSG = ('This message is generated when I trigger a silent alarm.\n\n'
              'PLEASE CALL 911 AND DIRECT THEM TO 11921 Triple Crown Rd, Reston.\n\n'
              'Use of the silent alarm indicates it is probably unwise to \n'
              'call or text me; if I had wanted an obvious response, \n'
              'I would have triggered a noisy panic.\n\n')

if DEBUG:
  SILENT_TO = ['ken@kenstillson.com', 'tech@point0.net']
  SILENT_SUBJ = SILENT_SUBJ.replace('URGENT', 'THIS IS A TEST - PLEASE IGNORE')

# --------------------

def announce(msg, push_level=None, syslog_level=None, details=None, speak=True):
  log_msg = f'announce [{speak=}/{push_level=}/{syslog_level=}]: {msg}'
  if details: log_msg += f': {details}'
  if DEBUG: return C.log_debug(f'ext would announce: {log_msg}')
  C.log(log_msg)
  if speak:
    rslt = C.read_web('http://pi1/speak/' + C.quote_plus(msg))
    if not '<p>ok' in rslt: C.log_error(f'unexpected result from speak command: {rslt}')
  if details: msg += ': %s' % details
  if push_level: push_notification(msg, push_level)
  if syslog_level: syslog.syslog(syslog_level, msg)


def control(target, command='on'):
  if DEBUG: return C.log_debug(f'ext would control {target} -> {command}')
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
  C.log(f'pushbullet sending [level={level}]: {msg}')
  if level != 'other': msg += ' !%s' % level
  ok = subprocess.call(["/usr/local/bin/pb-push", msg])
  if ok != 0: C.log_warning(f'pushbullet returned unexpected status {ok}')
  return ok == 0


def send_emails(from_addr, to, subj, contents):
  if DEBUG: return C.log_debug(f'ext would send email {to=} {subj=}')
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
  send_emails('ken@kenstillson.com', SILENT_TO, SILENT_SUBJ, SILENT_MSG)

