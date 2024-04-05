#!/usr/bin/python3
'''Linux process list scanner: identify unexpected processes.

It's not easy to generate an allowed-process list for computers that humans
use, but for servers running workloads that you control, the list of things
you expect them to do is often tractible and changes reasonably slowly.

At regular intervals (every few minutes by default), procmon will scan all the
processes running on a system, and compare each to a configured white-list.
Any 'unexpected' processes will raise an alert.  In addition, white-list
entries can be listed as 'required,' meaning that an alert is raised if that
process is *not* seen.

White-list (WL) entries are identified by the combination of which docker
container they are in ('/' for not in a container, '*' for any container), the
user who owns the process ('*' for any user), and a regular expression for the
command-line of the process.  WL entries can also be tagged as
"allow_children," which will automatically accept all child processes from the
given one.  This can be helpful for services you trust that can launch many
different subprocesses, and where you can't be bothered to catelog them all.

procmon does not push alerts, rather, it is expectes some other monitoring
system (e.g. nagios) will check the /healthz path on procmon's web-server.  If
no alert is pending, this handler outputs "all ok", otherwise a short
human-readable description of the alert condition is output.

Assuming the user does not set --queue="", alerts are 'sticky,' meaning that
even when the condition that raised an alert goes away, the alert remains.
This is so that alerts are not missed for processes that are noticed by
procmon but then exists.  Sticky alerts are stored in the file specified by
the --queue flag (by default /var/procmon/queue), and the queue is cleared
simply by emptying or deleting this file.

WARNING: procmon supports a "/zap" handler that will clear the queue via a
http GET request, with no particular authentication requirements.  If you're
not in a trusted environment, you'll want to make sure that's disabled.
(/zap does send a critical level syslog message, see flag --no-syslog)

procmon is one of the few services I run outsied a Docker container.  It needs
to be running on the real host in order to have visibility into all the
system's processes.  This outside-a-container position makes procmon a good
place to check a number of other security-like conditions, so a bunch of other
checks are added-on.

Specifically- procmon can run d-cowscan (see ../../container-infrastructure),
which identifies unexpected copy-on-write filesystem changes inside
containers.  Additionally, procmon can check to see if the root filesystem is
mounted read-only; I generally keep mine locked-down, and it's handy for
procmon to let me know if I (accidentally) or someone else (deliberately?!)
unlocks it.  These additional checks can easily be turned off in the flags.

Note that d-cowscan and d-map (which is used to map between human-readable
container names and the Docker-assigned container id numbers) both need to be
run as root.  Other than that, procmon needs no privlidges other than the
ability to write to its queue and logfiles, so I generally run it as an
unprivlidged user, and then have procmon run d-map and d-cowscan via sudo.
This does mean you'll need corresponding /etc/sudoers entries for whatever
user you run procmon as.

Note that a procmon scan is moderately expensive in terms of CPU time- there's
lots of list scanning and regular expression lookups going on.  Therefore,
procmon will generally perform its scan at regular intervals (see --delay),
and cache the results.  When procmon is queried (via its web interface), it
returns the results from the most recent scan.  However, there is also a /scan
handler to perform an on-demand scan.  This is useful if you think you've
cleared something up, and want to check that procmon is 'all ok' now.
However, this opens up a possible denial-of-service route by overwhelming
procmon with /scan requests.  If you're not in a trusted environment, you'll
want to disable that handler.

Finally, it is worth noting that procmon true security value is somewhat
limited by the fact that it only scans every few minutes: it can easily miss
short lived processes.  This makes it much more useful when attackers don't
know that it's there, and so will be less careful about leaving around
exploritory processes, open shells, etc.

It would be possible to intercept every process launch (for example by
integrating with auditd), but that would be much more invasive and higher-risk
if something were to go wrong.  procmon isn't perfect, but it's pretty good,
at least if attackers don't know about it.

# Note to self: procmon uses psutil to scan the proc tree; good reference:
# https://pypi.python.org/pypi/psutil/1.2.1

'''

import argparse, psutil, os, re, subprocess, sys, time
from dataclasses import dataclass
from typing import List

import kcore.common as C
import kcore.html as H
import kcore.uncommon as UC
import kcore.varz as V
import kcore.webserver as W


# ---------- Control constants

WEB_HANDLERS = {
  '/':        lambda request: root_handler(request),
  '/healthz': lambda request: healthz_handler(request),
  '/pstree':  lambda request: pstree_handler(request),
  '/scan':    lambda request: scan_handler(request),
  '/zap':     lambda request: zap_handler(request),
}

# ---------- Global state & types

ARGS = None
DOCKER_MAP = {}          # Maps container id (str) to container name (str).  popualted by get_docker_map()
SCANNER = None           # Singleton of current scanner instance.
UNEXPECTED_PREV = set()  # set of pids from the previous scan, used for change detection.
WL = None                # List[WL] (see procmon_whitelist.py)


@dataclass
class ProcessData:
  # desc: str  -- created by __post_init__
  pid: int
  container_name: str
  ppid: int
  username: str
  child_pids: List[int]
  cmdline: str
  name: str
  note: str = None
  def __post_init__(self):
    note = '[[ ** %s ** ]] ' % self.note if self.note else ''
    self.desc = '[%-9s](%-5s/%-5s) %s%s@%.120s' % (
      self.container_name, self.pid, self.ppid, note, self.username, self.cmdline)
  def __str__(self): return desc


# ---------- general helpers

def get_docker_map():
  '''returns dict: cid:str -> container_name:str'''
  cid_map = {}
  for i in C.popener(['/usr/bin/sudo', '/root/bin/d-map']).strip().split('\n'):
    if not i: continue
    if not ' ' in i:
      C.log_error(f'unexpected output from d-map: {i}')
      continue
    cid, name = i.split(' ', 1)
    cid_map[cid] = name
  C.log_debug(f'procmap: {cid_map}')
  return cid_map


def now(): return int(time.time())


def is_file_populated(filename):
  if not filename: return False
  if not os.path.isfile(filename): return False
  if os.path.getsize(filename) == 0: return False
  return True


# ---------- scanner business logic

class Scanner(object):
  def __init__(self):
    self.cow_errors = []         # List of error msg strings
    self.expected = set()        # set of pids
    self.other_errors = []       # List of error msg strings
    self.missing = []            # List of WL.WL entries
    self.pd_db = {}              # map from pid to ProcessData instance
    self.unexpected = set()      # set of pids
    self.greylisted = set()      # set of pids
    for entry in WL.WHITELIST: entry.last_scan_hits = 0

  # ----- scanning

  def scan(self):
    C.log("start scan")
    V.bump('scans')
    V.stamp('last_scan')

    global DOCKER_MAP
    DOCKER_MAP = get_docker_map() if not ARGS.nodmap else {}

    self.add_process(1, '/')
    if not ARGS.nocow:    self.scan_cow()
    if not ARGS.noro:     self.scan_ro()
    if not ARGS.nodupchk: self.scan_dup_uids()

    # Check for missing processes.
    for entry in WL.WHITELIST:
      if entry.required and entry.hit_count_last_scan == 0:
        self.missing.append(entry)

    # Separate out just the new problems for adding to the queue.
    global UNEXPECTED_PREV
    new_unexpected = self.unexpected - UNEXPECTED_PREV
    UNEXPECTED_PREV = set(self.unexpected)

    # Outputs
    new_problems = self.problems_to_list_of_strings(new_unexpected, False)
    for i in new_problems: C.log(i)
    if ARGS.queue and new_problems:
      with open(ARGS.queue, 'a') as f: f.write('\n'.join(new_problems) + '\n')
    if ARGS.output:
      with open(ARGS.output, 'w') as f: f.write(str(WL.WHITELIST).replace(' WL', '\n WL'))

  def scan_cow(self):
    for i in C.popener(['/usr/bin/sudo', '/root/bin/d-cowscan']).strip().split('\n'):
      if 'all ok' in i: continue
      self.cow_errors.append(i)

  def scan_dup_uids(self):
    c_uids = {}   # maps usernames to set of container names
    for pd in self.pd_db.values():
      if not pd.container_name: continue
      if 'root' in pd.username: continue
      if not pd.username in c_uids: c_uids[pd.username] = set()
      c_uids[pd.username].add(pd.container_name)
    for username in c_uids:
      skip = False
      for i in c_uids[username]:
        if 'nextcloud' in i: skip = True
      if skip: continue
      if username == 'dken': continue
      if len(c_uids[username]) > 1: self.other_errors.append(f'{username} appears in multiple containers: {c_uids[username]}')

  def scan_ro(self):
    stat = os.statvfs('/')
    ro = bool(stat.f_flag & os.ST_RDONLY)
    if not ro: self.other_errors.append('root not mounted read only')


  # ----- psutil -> ProcessData

  def get_process_data(self, pid, container_name='?'):
    p = psutil.Process(pid)
    cmd_list = p.cmdline()
    out = ProcessData(
        pid = p.pid,
        container_name = container_name,
        ppid = p.ppid(),
        username = p.username(),
        child_pids = [i.pid for i in p.children(recursive=False)],
        cmdline = ' '.join(cmd_list),
        name = cmd_list[0])
    self.pd_db[out.pid] = out
    return out


  # ----- process tree building ("p" is psutil process object instances)

  def add_process(self, pid, container_name):
    try:
      pd = self.get_process_data(pid, container_name)
    except Exception as e:
      C.log_error(f'Skipping pid with convertion error (usually a defunct process): {pid}: {str(e)}')
      return

    wl = self.find_whitelist_entry(WL.WHITELIST, pd)
    if wl:
      wl.hit_last = now()
      wl.hit_count += 1
      wl.hit_count_last_scan += 1
    C.log_debug('proc: %s; wl: %s' % (pd.desc, wl))

    if not wl:  # first check if its on the greylist.
      gl = self.find_whitelist_entry(WL.GREYLIST, pd)
      if gl:
        C.log_debug('proc: %s; gl: %s' % (pd.desc, gl))
        gl.hit_last = now()
        gl.hit_count += 1
        gl.hit_count_last_scan += 1
        return self.add_to_pset(self.greylisted, pd)

      else:  # Neither whitelist nor greylist; this is an unexpected process.
        C.log_debug('UNEXPECTED: %s' % pd.desc)
        return self.add_to_pset(self.unexpected, pd)

    if wl.allow_children:
      return self.add_to_pset(self.expected, pd, 'allowed w/ children')

    # Not auto-accepting-children, so add the children for inspection.
    self.add_to_pset(self.expected, pd)
    if 'containerd-shim' in pd.name: return self.add_docker_tree(pd)
    if '/usr/bin/conmon' in pd.name: return self.add_docker_tree(pd)
    self.add_pid_list(pd.child_pids, container_name)


  def add_docker_tree(self, pd):
    shim_children_pids = pd.child_pids
    try:
      # old docker; TODO(defer): auto-detect
      # init_pid = shim_children_pids[0]
      # with open('/proc/%s/cpuset' % init_pid) as f: cpuset = f.readline()
      # cid = cpuset.replace('/docker/', '')[:12]
      init_pid = pd.pid
      with open(f'/proc/{init_pid}/cmdline', mode='rb') as f: cmdline = f.read()
      parts = cmdline.split(b'\0')
      for i, part in enumerate(parts):
        if part == b'-id':
          cid = parts[i + 1].decode()[:12]
          C.log_debug(f'pid {init_pid}: got cid from -id (docker style): {cid}')
          break
        elif part.startswith(b'/usr/bin/conmon'):
          cid = parts[i + 4].decode()[:12]
          C.log_debug('pid {init_pid}: got cid from conmon (podman style): {cid}')
          break
      else:
        return self.add_error_process(pd, f'unable to get container id for pid {init_pid}')
      cname = DOCKER_MAP.get(cid, f'cid:{cid}')
    except Exception as e:
      return self.add_error_process(pd, f'Unable to parse docker shim; {cpuset=}, {cid=}, {match=}, {cname=}, {e=}')

    # We have a container name, so add the subtree.
    C.log_debug('adding container subtree. parent pid=%d, cname=%s, cid=%s, children=%s' % (pd.pid, cname, cid, shim_children_pids))
    self.add_pid_list(shim_children_pids, cname)


  def add_pid_list(self, pid_list, container_name):
    for pid in pid_list: self.add_process(pid, container_name)


  def add_error_process(self, pd, note):
    self.add_to_pset(self.unexpected, pd, note)


  # ---------- ProcessData-based methods
  # ("pd" is always a ProcessData instance)

  def add_to_pset(self, pset, pd, note=''):
    if pd.cmdline == '':
      C.log_debug(f'skipping add of process with empty cmdline: {pd.desc}')
      return
    if note: pd.note = note
    pset.add(pd.pid)

  def is_all_ok(self):
    return len(self.missing) == 0 and len(self.expected) > 10 and len(self.unexpected) == 0 and len(self.cow_errors) == 0 and len(self.other_errors) == 0

  # -----

  def find_whitelist_entry(self, search_list, pd):
    for w in search_list:
      if ((w.user == '*' or w.user == pd.username) and
          (w.container_name == '*' or w.container_name == pd.container_name)):
        if w.pattern.match(pd.cmdline): return w

  def problems_to_list_of_strings(self, unexpected_pids, expand_trees=False):
    out = []
    for pid in unexpected_pids:
      pd = self.pd_db[pid]
      out.append('unexpected: %s' % self.proctree_to_string(pd) if expand_trees else pd.desc)
    for ce in self.cow_errors: out.append('COW: %s' % ce)
    for ce in self.other_errors: out.append('FS: %s' % ce)
    for m in self.missing: out.append('missing: %s' % m)
    return sorted(out)

  def proctree_to_string(self, pd):
    level = 0
    str = ''
    while pd:
      for i in range(level + 1): str += ' '
      str += pd.desc
      str += '\n'
      pd = self.pd_db.get(pd.ppid, None)
      level += 1
    return str

  def render_pset_to_table(self, title, pset):
    rows = []
    if pset:
      for pid in pset:
        pd = self.pd_db[pid]
        rows.append([pd.container_name, pd.pid, pd.ppid, pd.note, pd.username, pd.cmdline[:40]])
    else:
      rows.append([title, 'all ok'])
    return H.list_to_table(rows, title=title)


# ---------- handler helpers

def render_other_errors_to_table(title, cow_errors, other_errors):
  rows = []
  if cow_errors:
    for ce in cow_errors: rows.append(['cow scan', ce])
  else: rows.append(['cow scan', 'all ok'])
  if other_errors:
    for fe in other_errors: rows.append(['Other scans', fe])
  else: rows.append(['Other scans', 'all ok'])
  return H.list_to_table(rows, title=title)


def render_queue_to_table(title):
  rows = []
  if not os.path.isfile(ARGS.queue): return ''
  with open(ARGS.queue) as f:
    for line in f: rows.append([line + '<br/>'])
    return H.list_to_table(rows, title=title)


def render_missing_to_table(missing):
  rows = []
  if missing:
    for m in missing: rows.append([m])
  else: rows.append(['missing', 'all ok'])
  return H.list_to_table(rows, title='missing')


def varz_to_table(list_of_varz):
  return H.list_to_table([[i, V.get(i)] for i in list_of_varz], title='varz')


# ---------- handlers

def root_handler(request):
  is_all_ok = SCANNER.is_all_ok() and not is_file_populated(ARGS.queue)
  out = H.wrap('OK' if is_all_ok else 'Error', 'h2')
  out += render_queue_to_table('queue')
  out += varz_to_table(['last_scan', 'scans'])
  out += SCANNER.render_pset_to_table('unexpected', SCANNER.unexpected)
  out += render_other_errors_to_table('other errors', SCANNER.cow_errors, SCANNER.other_errors)
  out += render_missing_to_table(SCANNER.missing)
  out += SCANNER.render_pset_to_table('greylisted', SCANNER.greylisted)
  out += SCANNER.render_pset_to_table('expected', SCANNER.expected)
  return H.html_page_wrap(out, 'procmon')


def healthz_handler(request):
  if is_file_populated(ARGS.queue):
    return 'ERROR: queue alert' if SCANNER.is_all_ok() else 'ERROR: queue alert (still active)'
  if SCANNER.is_all_ok(): return 'all ok'

  summary = 'ERROR'
  out = ''
  for i, err in enumerate(SCANNER.problems_to_list_of_strings(SCANNER.unexpected, False)):
    out += '\n%s' % err
    C.log(err)
    if i >= 10:
      summary = 'ERROR OVERFLOW'
      C.log_alert('procmon scan with overflow bad results.')
      break
  return f'{summary}\n\n{out}'


def pstree_handler(request):
  return C.popener(['/bin/ps', 'aux', '--forest'])


def scan_handler(request):
  if ARGS.no_scan_handler: return W.Response('manual scan disabled', status_code=403)
  new_scanner = Scanner()
  new_scanner.scan()
  global SCANNER
  SCANNER = new_scanner
  return root_handler(request)


def zap_handler(request):
  if ARGS.no_zap_handler: return W.Response('zap disabled', status_code=403)
  with open(ARGS.queue, 'w') as f: pass
  C.log_critical('procmon queue cleared by /zap request')
  return 'zapped'


# ---------- main

def parse_args(argv):
  parser = C.argparse_epilog(description='process scanner')
  parser.add_argument('--debug',   '-D',   action='store_true', help='output debugging data to stdout (works best with -t)')
  parser.add_argument('--delay',   '-d',   type=int, default=120, help='delay between automatic rescans (seconds)')
  parser.add_argument('--logfile', '-l',   default='/var/log/procmon.log', help='where to write deviation log; contains timestamp and proc tree context for unexpected items.  Blank to disable.')
  parser.add_argument('--nocow',           action='store_true', help='skip COW scan (used for testing)')
  parser.add_argument('--nodmap',          action='store_true', help='skip getting the map from container ids to names.  Mainly for testing (avoids a sudo call), as makes whitelist entries based on container names useless.')
  parser.add_argument('--nodupchk',        action='store_true', help='skip checking if the same uid (other than root) is used in multiple containers.')
  parser.add_argument('--noro',            action='store_true', help='skip root-read-only check (used for testing)')
  parser.add_argument('--no-scan-handler', action='store_true', help='do not allow use of demand /scan')
  parser.add_argument('--no-syslog',       action='store_true', help='do not send critical level logs to syslog')
  parser.add_argument('--no-zap-handler',  action='store_true', help='do not allow clearing the alert queue via /zap')
  parser.add_argument('--output',  '-o',   default='/var/procmon/output', help='filename for statistics from last scan')
  parser.add_argument('--port',    '-p',   type=int, default=8080, help='web port to listen on.  0 to disable.')
  parser.add_argument('--queue',   '-q',   default='/var/procmon/queue', help='where to put the queue of current unexpected items from the most recent scan')
  parser.add_argument('--test',    '-t',   action='store_true', help='run single scan and output only to stdout')
  parser.add_argument('--whitelist', '-w', default='procmon_whitelist', help='name of file contianing whitelist data')
  return parser.parse_args(argv)


def main(argv=[]):
  global ARGS
  ARGS = parse_args(argv or sys.argv[1:])
  C.init_log('procmon', ARGS.logfile,
             filter_level_stderr=C.DEBUG if ARGS.debug else C.NEVER,
             filter_level_syslog=C.NEVER if ARGS.no_syslog else C.CRITICAL)

  global WL
  WL = UC.load_file_as_module(ARGS.whitelist)
  for entry in WL.WHITELIST: entry.pattern = re.compile(entry.regex)
  for entry in WL.GREYLIST: entry.pattern = re.compile(entry.regex)

  global SCANNER
  SCANNER = Scanner()

  if ARGS.test:
    ARGS.queue = ''
    ARGS.logfile = ''
    SCANNER.scan()
    out = '\n'.join(SCANNER.problems_to_list_of_strings(SCANNER.unexpected, True))
    print(out or 'all ok')
    return 0

  ws = W.WebServer(WEB_HANDLERS, wrap_handlers=not ARGS.debug)
  ws.start(port=ARGS.port)
  ws.add_handlers(WL.ADDL_HANDLERS)

  SCANNER.scan()
  while True:
    time.sleep(ARGS.delay)
    new_scanner = Scanner()
    new_scanner.scan()
    SCANNER = new_scanner


if __name__ == '__main__':
  sys.exit(main())
