#!/usr/bin/python3

'''Service to watch files/directories for problems.

The primary idea of filewatch is to scan log files that are expected to change
frequently for a lack of change.  i.e. to enable an alert when the last
modiciation time for a monitored file is too old.

It's also grown a few extra types of monitoring, for example, it can enable an
alert is a file (like an error log) that's expected to be empty is not empty,
or if a file contains a particular string (indicating an alarming condition).

filewatch does not push alert messages, instead, it is expected to be
monitored via it's web interface.  The "/healthz" handler will return the
simple string "all ok" if all is well, and some other short human-readable
error message if one or more alert conditions exist.  It's intended that the
/healthz handler will be monitored by something like Nagios.

The default handler (i.e. any web request path except /healthz) returns a
human-readable html table showing detailed scan results.

The config file (see --config flag) is just a Python file with a dict named
CONFIG, which maps file patterns to maximum allowed ages in seconds.  The file
patterns may contain glob expressions, or may be of the form
/dir/.../{NEWEST}, which will be replaced by the most recently modified file
in specified directory.  Note that direct file-name matches override glob
expressions when multiple rules match.

I've included one of my actual configurations as an example.

Note #1- my syslog-ng configuration (see
../../containers/syslogdock/files/etc/syslog-ng/syslog-ng.conf) is
designed to take messages from cron daemons and put them into separate files
named by the host they came from, i.e. /root/syslog/cron-{hostname}.log.  In
this way, I can have a glob rule for /root/syslog/cron* that will alert if any
host's cron logfile becomes too old.  As a neat advantage, I don't need to
register a new host to be monitored; whenever a new host starts sending its
logs to the centralized syslog-ng instance, it automatically gets it's own new
cron logfile, and the filewatch glob automatically picks it up on the next
run.

Note #2- filewatch scans are done "on-demand," i.e. every time the /healthz
handler is called, a new scan is run.  The simple scans from a single filename
to a max-age are quite inexpensive, but 'NOT-FOUND' scans (which launch grep
as a subprocess) can be much more expensive, especially if scanning large
files.  This basically assumes that filewatch is being run in a non-hostile
environment; there is no protection against receiving too many requests and
potentially DoS'ing filewatch itself or consuming lots of system resources.
See ../procmon for a slightly better written service that scans at an
internally set rate and caches the results, and just serves back the most
recent cached results when queried.  Perhaps filewatch should be re-written to
work that way...

'''

import argparse, os, glob, subprocess, sys, time
import kcore.common as C
import kcore.html as H
import kcore.webserver as W
import kcore.uncommon as UC
import kcore.varz as V


# ---------- control constants

CONFIG = {}     # Loaded by main() from config file.

MAX_LEN_IN_OUTPUT = 80

WEB_HANDLERS = {
  '/healthz':   lambda request: healthz_handler(request),
  None:         lambda request: default_handler(request),
}

# ---------- helpers

def find_newest_file(target):
  dirname = target.replace('/{NEWEST}', '')
  if not os.path.isdir(dirname): raise RuntimeError('not a dir: {dirname}')
  files = glob.glob(f'{dirname}/*')
  if not files: raise RuntimeError('no files for newest check')
  try:
    return max(files, key=os.path.getmtime)
  except Exception as e:
    raise RuntimeError(f'Exception finding newst file (possibly broken symlink?): {target}: {e}')


def grep(filename, target):
  return subprocess.call(['/bin/fgrep', '-q', target, filename])


# ---------- scanner business logic

class Scanner:
  def __init__(self):
    self.reset()

  def reset(self):
    self.summary = None
    self.details = {}

  def run_check(self, filename, rule):
      answer = self.check(filename, rule)
      if answer is None: return None
      self.details[filename] = answer
      return answer

  def run_scan(self):
    self.summary = 'all ok'
    for filename, rule in CONFIG.items():
      self.run_check(filename, rule)
    V.bump('scans')
    V.set('latest-summary', self.summary)
    V.set('num-rules', len(CONFIG))
    return self.summary, self.details


  def check(self, filename, rule):
    if not rule: return None   # rule is to skip this check.

    if '{NEWEST}' in filename:
      try:
        newest = find_newest_file(filename)
      except RuntimeError as e:
        return self.problem(f'find_newest failure {filename}: {str(e)}')
      self.run_check(newest, rule) + f': {newest}'
      return None  # Nothing more to check for the {NEWEST} rule itself.

    if '*' in filename:
      file_list = glob.glob(filename)
      if not file_list: return self.problem(f'glob failure: {filename}')
      for f in file_list:
        if f in CONFIG: continue  # Defer to more specific rule.
        self.run_check(f, rule)
      return None # Nothing more to check for the glob rule itself.

    if isinstance(rule, int):  # int => max age rule
      try:
        t = os.path.getmtime(filename)
        tstr = time.ctime(t)
        if ((time.time() - t) > rule): return self.problem(f'too old: {filename}: {tstr}')
        else: return self.ok(f'ok: {tstr}')
      except Exception as e:
        return self.problem(f'stat error: {filename}: {e}')

    if rule == 'DIR-EMPTY':
      if not os.path.isdir(filename): return self.problem(f'DIR-EMPTY not a dir: {filename}')
      found = glob.glob(f'{filename}/*')
      if found: return self.problem(f'NOT EMPTY: {filename}')
      else: return self.ok('ok: empty')

    if rule == 'FILE-EMPTY':
      if not os.path.isfile(filename): return self.problem(f'FILE-EMPTY not an existing file: {filename}')
      if os.path.getsize(filename) != 0: return self.problem(f'NOT EMPTY: {filename}')
      else: return self.ok('ok: empty')

    if rule.startswith('NOT-FOUND'):
      _, target = rule.split(':', 1)
      grep_status = grep(filename, target)
      if not os.path.isfile(filename): return self.problem(f'file not found: {filename}')
      if grep_status == 0: return self.problem(f'saw unexpected "{target}"')
      else: return self.ok(f'ok: not found: {target}')

    return self.problem(f'unknown rule: {filename}: {rule}')


  def ok(self, msg='ok'): return msg

  def problem(self, msg='?'):
    self.summary = 'ERROR'
    C.log_warning(msg)
    V.bump('problem_count_' + msg)
    return f'ERROR: {msg}'


# ---------- handlers

def healthz_handler(request):
  summary, _ = Scanner().run_scan()
  return summary


def default_handler(request):
  summary, details = Scanner().run_scan()
  out = H.wrap(summary, 'p')
  shortened_details = { (k[:(MAX_LEN_IN_OUTPUT-3)]+'...' if len(k) > MAX_LEN_IN_OUTPUT else k): v for k, v in details.items() }
  out += H.list_to_table(shortened_details)
  return H.html_page_wrap(out, 'filewatch')


# ---------- main

def main():
  parser = argparse.ArgumentParser(description='File age checker')
  parser.add_argument('--config', '-c', default='filewatch_config', help='Name of file with CONFIG dictionary.')
  parser.add_argument('--port', '-p',   type=int, default=8080, help='Port on which to start server.')
  parser.add_argument('--test', '-t',   action='store_true', help='Run a single scan and output to stdout, then quit.')
  args = parser.parse_args()

  # load configuration from file.
  global CONFIG
  tmp = UC.load_file_as_module(args.config)
  CONFIG = tmp.CONFIG  
  
  if args.test:
    summary, details = Scanner().run_scan()
    print(f'Overall status: {summary}')
    for f in sorted(details):
      print('%-30.30s : %s' % (f, details[f]))
    sys.exit(0)

  ws = W.WebServer(handlers=WEB_HANDLERS)
  ws.start(port=args.port, background=False)  # Does not return.


if __name__ == '__main__':
  sys.exit(main())
