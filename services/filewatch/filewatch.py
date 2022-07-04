#!/usr/bin/python3

'''TODO(doc)
'''

import argparse, os, glob, subprocess, sys, time
import kcore.common as C
import kcore.html as H
import kcore.webserver as W
import kcore.uncommon as UC
import kcore.varz as V


# ---------- control constants

CONFIG = {}     # Loaded by main() from config file.

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
    return max(files, key=os.path.getctime)
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
  out += H.list_to_table(details)
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
