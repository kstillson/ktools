#!/usr/bin/python3

'''web interface for scheduling/managing future http-get requests.'''

##@@ temp- path to live pylib dir
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../pylib'))
if sys.path[0] != p: sys.path.insert(0, p)



import datetime, time, smtplib, sys, textwrap
import dateparser as DP
from dataclasses import dataclass

import kcore.common as C
import kcore.html as H
import kcore.time_queue_persisted as TQP
import kcore.webserver as W
import kcore.varz as V


# ========== generic helpers

def es_now(): return int(time.time())

def safe_int(str_int):
    try: return int(str_int)
    except: return None


# ========== const

EMAIL_FROM = "tech@point0.net"
EMAIL_SUBJ = "atserver job output: "

HANDLERS = {
    '/':     lambda rqst: handler_root(rqst),
    '/add':  lambda rqst: handler_add(rqst),
    '/del':  lambda rqst: handler_del(rqst),
}

LOOP_TIME = 20   # seconds

RETAIN_DONE_QUEUE_FOR = 60 * 60    # 60 minutes in seconds


# ------------------------------ model ------------------------------

# ========== types

# QUEUE (below) will be an instance of TQP.TimeQueuePersisted.
# QUEUE.queue is a list of TQP.EventDC instances
# QUEUE.queue[x].kwargs contains the dict-ified verison of AtEvent contents.

@dataclass
class AtEvent:
    index: int
    url:   str
    name:  str = None
    out:   str = None   # "syslog", or "file:filename", or "email:dest@, or "stdout" (for cli) else app log
    notes: str = None


# ========== globals  (initialized by main)

ARGS = None         # rsult of parse_args
DONE_QUEUE = []     # ordered list of EventDC's
NEXT_INDEX = 0
QUEUE = None        # instance of TQP.TimeQueuePersisted

# ========== model methods

def make_atevent(url, name=None, out=None, notes=None):
    global NEXT_INDEX
    e = AtEvent(NEXT_INDEX, url, name, out, notes)
    NEXT_INDEX += 1
    return e

def add(url, dt, name=None, out=None, notes=None):
    if not url.startswith('http'): url = 'http://' + url
    atevent = make_atevent(url, name, out, notes)
    edc = TQP.EventDC(dt, 'fire_and_get_url', args=[], kwargs=atevent.__dict__)
    QUEUE.add_event(edc)


def del_index(index: int) -> bool:
    for i, edc in enumerate(QUEUE.queue):
        if edc.kwargs.get('index') == index:
            with QUEUE._p.get_rw() as d:
                rm = d.pop(i)
                C.log(f'removed event index {index}: {str(rm)}')
                return True
    C.log_error('unsuccessful attempt to remove index {index}')
    return False


def prune_done_queue():
    global DONE_QUEUE
    max_dt = datetime.datetime.now() - datetime.timedelta(seconds=RETAIN_DONE_QUEUE_FOR)
    rm = []
    for i, d in enumerate(DONE_QUEUE):
        if d['when'] < max_dt: rm.append(i)
    if not rm: return
    for i in sorted(rm, reverse=True): DONE_QUEUE.pop(i)
    C.log(f'pruned {len(rm)} old events from done queue.')
    return len(rm)


# ------------------------------ controller ------------------------------

def fire_and_get_url(**kwargs) -> None:   # called by TQ.Event.fire()
    now = datetime.datetime.now()

    atevent = AtEvent(**kwargs)
    resp = C.web_get(atevent.url, ARGS.timeout)
    if resp.ok:
        out = resp.text
        V.bump('fired:ok')
    elif resp.exception:
        out = f'Exception: {resp.exception}'
        V.bump('fired:exception')
    else:
        out = f'Error code={resp.status_code} result={resp.text}'
        V.bump('fired:error')

    # Always send output to the log
    C.log(f'fired event {atevent}  -> {resp.ok=}  output: {out or "(no output)"}', C.INFO if resp.ok else C.ERROR)

    # Append to DONE_QUEUE
    kwargs['when'] = now
    kwargs['output'] = out
    kwargs['status'] = resp.status_code
    DONE_QUEUE.append(kwargs)

    # Anywhere else to send the output?
    dest = atevent.out

    target = None
    if ':' in dest: dest, target = dest.split(':', 1)

    if dest == 'syslog':   C.log_syslog(out, level=C.INFO if resp.ok else C.ERROR, ident=sys.argv[0])
    elif dest == 'stdout': print(out)
    elif dest == 'file':
        with open(target, 'a') as fil: fil.write(out + '\n')
    elif dest == 'email':
        with smtplib.SMTP() as s:
            msg = textwrap.dedent(f'From: {EMAIL_FROM}\nTo: {target or "root"}\nSubject: {EMAIL_SUBJ}: {atevent.name}\n\n{out}\n')
            C.log(f'sending email: ' + msg.replace('\n', '; '))
            s.connect()
            s.sendmail(EMAIL_FROM, [target], msg)


def text_to_datetime(txt):
    return DP.parse(txt, languages=['en'],
                    settings={'PREFER_DATES_FROM': 'future',
                              'PREFER_DAY_OF_MONTH': 'first'})


# ------------------------------ view (web server) ------------------------------

def handler_root(request):
    out = '<p>'

    tab = []
    now = datetime.datetime.now()
    for edc in QUEUE.get_queue_ro():
        atevent = AtEvent(**edc.kwargs)
        delta = edc.fire_dt - now
        when_mins = round(delta.total_seconds() / 60, 1)
        controls = f'<button onclick="window.location.href=\'del?index={atevent.index}\';">del</button>\n'
        tab.append([controls, atevent.index, edc.fire_dt, when_mins, atevent.name, atevent.notes[:30], atevent.url[:30], atevent.out ])

    out += H.list_to_table(tab, table_fmt='border="1" cellpadding="5"',
                           header_list=['controls', 'index', 'when', '+mins', 'name', 'notes', 'url', 'out'],
                           title='Queued events')

    out += '''
  <p>Add an event:</p>
  <form action="add" method="post" style="display: inline;">
    <table border="1" cellpadding="5">
      <tr><td>When</td>  <td><input name="when" size="20"></td></tr>
      <tr><td>Name</td>  <td><input name="name" size="20"></td></tr>
      <tr><td>URL</td>   <td><input name="url"  size="30"></td></tr>
      <tr><td>Output</td><td><input name="out"  size="20"></td></tr>
    </table><br/>
    <input type="submit" value=" add ">
  </form>
'''

    if DONE_QUEUE:
        out += '<p/>'
        tab = []
        for d in DONE_QUEUE:
            tab.append([d['index'], d['when'], d['name'], d['notes'], d['url'], d['output'], d['out']])
        out += H.list_to_table(tab, table_fmt='border="1" cellpadding="5"',
                               header_list=['index', 'fired at', 'name', 'notes', 'url', 'output', 'sent-to'],
                               title='Recently completed events')

    return H.html_page_wrap(out, 'At-server')


def handler_add(request):
    cont = '<p><a href=".">continue</a></p>'

    when = text_to_datetime(request.post_params.get('when'))
    if not when: return 'add: unable to parse provided time.' + cont

    name = request.post_params.get('name')
    if not name: name = '(anonymous)'

    url = request.post_params.get('url')
    if not url: return 'add: unable to parse provided URL.' + cont

    out = request.post_params.get('out')
    user = os.environ.get('REMOTE_USER') or 'unknown'
    notes = f'created {es_now()} by {user}'

    add(url, when, name, out, notes)
    return f'<p>ok: added event index {NEXT_INDEX - 1}\n{cont}'


def handler_del(request):
    index = safe_int(request.get_params.get('index'))
    ok = del_index(index)
    out = '<p>delete: ok' if ok else 'delete: failed'
    out += '<p><a href=".">continue</a></p>'
    return out


# ========== main

def parse_args(argv):
  ap = C.argparse_epilog()
  ap.add_argument('--filename', '-F', default='atserver_queue.persist', help='filename for persisted queue')
  ap.add_argument('--logfile',  '-L', default='atserver.log', help='logfile name; use "-" for stdout.')
  ap.add_argument('--port',     '-P', default=8080, help='html service port.  0 to disable.')
  ap.add_argument('--timeout',  '-T', default=5, help='html get timeout (seconds)')

  g1 = ap.add_argument_group('CLI add an event')
  g1.add_argument('--add',  '-a',  action='store_true', help='add a queued item')
  g1.add_argument('--name', '-n',  default='anonymous', help='name for the item')
  g1.add_argument('--out' , '-o',  default='stdout',    help='what to do with any output')
  g1.add_argument('--time', '-t',  default='',          help='when to run (~free text)')
  g1.add_argument('--url',  '-u',  default='',          help='url to retrieve')

  g2 = ap.add_argument_group('CLI for other alternate run-modes')
  g2.add_argument('--check','-c',  action='store_true',    help='just run all past-due events and exit')
  g2.add_argument('--list', '-l',  action='store_true',    help='list the current queue')
  g2.add_argument('--parse','-p',  action='store_true',    help='just parse the time provided by --time and exit')
  g2.add_argument('--rm',   '-r',  type=int, default=None, help='remote an item by index')

  return ap.parse_args(argv)


def main(argv=[]):

    # ---- init

    global ARGS
    ARGS = parse_args(argv or sys.argv[1:])
    C.init_log(sys.argv[0], logfile=ARGS.logfile)

    global QUEUE
    context = sys.modules[__name__]
    QUEUE = TQP.TimeQueuePersisted(ARGS.filename, context)

    global NEXT_INDEX
    for edc in QUEUE.queue:
        edc_index = edc.kwargs.get('index')
        if edc_index > NEXT_INDEX: NEXT_INDEX = edc_index
        NEXT_INDEX += 1
    C.log(f'loaded {len(QUEUE.queue)} persisted events and initialized {NEXT_INDEX=}')

    if ARGS.time: when = text_to_datetime(ARGS.time)

    # ---- Alternate run modes

    if ARGS.add:
        note = f'added via CLI at {es_now()}'
        if not when: sys.exit('unable to parse provided time.')
        add(ARGS.url, when, ARGS.name, ARGS.out, note)
        print(f'added index {NEXT_INDEX - 1}')
        return 0

    elif ARGS.check:
        cnt = QUEUE.check()
        print(f'ran {cnt} past-due events.')
        return 0

    elif ARGS.list:
        for edc in QUEUE.queue:
            atevent = AtEvent(**edc.kwargs)
            when = edc.fire_dt.strftime('%c')
            print(f'{atevent.index}\t {when}\t {atevent.name}\t {atevent.url}\t {atevent.out}\t {atevent.notes}')
        return 0

    elif ARGS.parse:
        if not when: sys.exit('unable to parse provided time.')
        print(when.strftime('%c'))
        return 0

    elif ARGS.rm is not None:
        ok = del_index(ARGS.rm)
        print(f'del index {ARGS.rm} : {ok}')
        return 0 if ok else -1

    # ---- Primary run mode: launch web-server and start checking loop.

    if ARGS.port: W.WebServer(handlers=HANDLERS).start(port=ARGS.port)
    while True:
        QUEUE.check()
        prune_done_queue()
        time.sleep(LOOP_TIME)


if __name__ == '__main__':  sys.exit(main())
