#!/usr/bin/python3

'''web interface for scheduling/managing future http-get requests.'''


import datetime, ephem, os, re, time, smtplib, sys, textwrap
import dateparser as DP
from dataclasses import dataclass

import kcore.common as C
import kcore.html as H
import kcore.time_queue_persisted as TQP
import kcore.webserver as W
import kcore.varz as V


# ========== generic helpers

def es_now(): return int(time.time())

def safe_float(str_float):
    try: return float(str_float)
    except: return None

def safe_int(str_int):
    try: return int(str_int)
    except: return None

def send_email(to, mail_from, subj, text):
    with smtplib.SMTP() as s:
        msg = textwrap.dedent(f'From: {mail_from}\nTo: {to}\nSubject: {subj}\n\n{text}\n')
        C.log(f'sending email: ' + msg.replace('\n', '; '))
        s.connect()
        s.sendmail(mail_from, [to], msg)


# ========== const

EMAIL_FROM = "tech@point0.net"
EMAIL_SUBJ = "atserver job output: "

HANDLERS = {
    '/':     lambda rqst: handler_root(rqst),
    '/add':  lambda rqst: handler_add(rqst),
    '/del':  lambda rqst: handler_del(rqst),
    '/varz': lambda rqst: handler_varz(rqst),
}

# for sunset lookup via ephem
LAT = '38.928'
LONG = '-77.357'

LOOP_TIME = 20   # seconds


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
    out:   str = None   # "syslog", or "file:filename", or "email:dest@, or "err-email:dest@", or "stdout" (for cli) else app log
    notes: str = None
    retries: int = 0


# ========== globals  (initialized by main)

ARGS = None         # rsult of parse_args
DONE_QUEUE = []     # ordered list of EventDC's
NEXT_INDEX = 0
QUEUE = None        # instance of TQP.TimeQueuePersisted

# ========== model methods

def make_atevent(url, name=None, out=None, notes=None, retries=None):
    global NEXT_INDEX
    if retries is None: retries = ARGS.default_retries
    if out is None: out = ARGS.default_output
    e = AtEvent(NEXT_INDEX, url, name, out, notes, retries)
    NEXT_INDEX += 1
    return e

def add(url, dt, name=None, out=None, notes=None, retries=None):
    if not url.startswith('http'): url = 'http://' + url
    if not dt:
        C.log_error('Cannot add event to queue without datetime')
        return None
    atevent = make_atevent(url, name, out, notes, retries)
    edc = TQP.EventDC(dt, 'fire_and_get_url', args=[], kwargs=atevent.__dict__)
    QUEUE.add_event(edc)
    C.log(f'added: {str(edc)}')
    V.bump('added:ok')
    return atevent.index


def del_index(index: int) -> bool:
    for i, edc in enumerate(QUEUE.queue):
        if edc.kwargs.get('index') == index:
            with QUEUE._p.get_rw() as d:
                atevent_dict_to_done_queue(edc.kwargs, 'CANCELLED', -99)
                rm = d.pop(i)
                C.log(f'removed event index {index}: {str(rm)}')
                V.bump('del:ok')
                return True
    C.log_error('unsuccessful attempt to remove index {index}')
    V.bump('del:err')
    return False


def prune_done_queue():
    global DONE_QUEUE
    max_dt = datetime.datetime.now() - datetime.timedelta(hours=ARGS.keep)
    V.set('done_prune_time', str(max_dt))
    rm = []
    for i, d in enumerate(DONE_QUEUE):
        if d['when'] < max_dt: rm.append(i)
    if not rm: return
    V.inc('pruned', len(rm))
    for i in sorted(rm, reverse=True): DONE_QUEUE.pop(i)
    C.log(f'pruned {len(rm)} old events from done queue.')
    return len(rm)


# ------------------------------ controller ------------------------------

def atevent_dict_to_done_queue(kwargs, out, code):
    kwargs['when'] = datetime.datetime.now()
    kwargs['output'] = out
    kwargs['status'] = code
    DONE_QUEUE.append(kwargs)


def fire_and_get_url(**kwargs) -> None:   # called by TQ.Event.fire()
    atevent = AtEvent(**kwargs)
    resp = C.web_get(atevent.url, ARGS.timeout)
    resp_ok = resp.ok

    if resp_ok and 'error' in resp.text.lower():
        resp_ok = False
        V.bump('mapped-ok-to-error')
        C.log_warning(f'mapped response status to error due to output content: {resp.text}')

    if resp_ok:
        out = resp.text
        V.bump('fired:ok')
    elif resp.exception:
        out = f'Exception: {resp.exception}'
        V.bump('fired:exception')
    else:
        out = f'Error code={resp.status_code} result={resp.text}'
        V.bump('fired:error')

    C.log(f'fired event {atevent}  -> {resp_ok=}  output: {out or "(no output)"}', C.INFO if resp_ok else C.ERROR)

    atevent_dict_to_done_queue(kwargs, out, resp.status_code)

    # ---- process output

    dest = atevent.out or ARGS.default_output or 'log'
    target = None
    if ':' in dest: dest, target = dest.split(':', 1)

    if dest == 'syslog':   C.log_syslog(out, level=C.INFO if resp_ok else C.ERROR, ident=sys.argv[0])
    elif dest == 'stdout': print(out)
    elif dest == 'file':
        with open(target, 'a') as fil: fil.write(out + '\n')
    elif dest == 'email':
        send_email(target or "root", EMAIL_FROM, f'{EMAIL_SUBJ}: {atevent.name}', out)
    elif dest == 'err-email' and not resp_ok:
        send_email(target or "root", EMAIL_FROM, f'{EMAIL_SUBJ}: {atevent.name}', out)

    # ---- retries?

    if not resp_ok and atevent.retries:
        dt = text_to_datetime(f'now + {ARGS.retry_secs}s')
        retries = safe_int(atevent.retries) - 1
        notes = f'RETRY ({retries} remain); {atevent.notes}'
        idx = add(atevent.url, dt, atevent.name, atevent.out, notes, retries)
        C.log(f'queued retry event index {idx}')
        V.bump('retries-queued')


def sunset(lat=LAT, long=LONG) -> datetime:
    ob = ephem.Observer()
    ob.lat = lat
    ob.long = long
    sun = ephem.Sun()
    sun.compute()
    return ephem.localtime(ob.next_setting(sun))


def text_to_datetime(txt):
    try:
        return text_to_datetime_real(txt)
    except Exception as e:
        C.log_error(f'error parsing text into date: {txt} -> {str(e)}')
        return None


def text_to_datetime_real(txt):
    parts = txt.split('+')

    base = parts.pop(0).strip() or 'now'
    if base == 'sunset': start = sunset()
    else: start = DP.parse(base, languages=['en'], settings={'PREFER_DATES_FROM': 'future', 'PREFER_DAY_OF_MONTH': 'first'})
    C.log_debug(f'base time: {base} -> {start}')

    delta = datetime.timedelta(0)
    for adj in parts:
        pattern = re.compile(r'^ *(-?[0-9\.]+) *([a-z]*)')
        match = pattern.match(adj)
        if not match: C.log_error(f'invalid adjustment format: {adj}; ignored.'); continue
        num = safe_float(match.group(1))
        if not num: C.log_error(f'invalid adjustment numeric potion: {str(match.group(1))}; ignored.'); continue
        unit = match.group(2)[0]
        if   unit.startswith('s'): delta += datetime.timedelta(seconds=num)
        elif unit.startswith('m'): delta += datetime.timedelta(minutes=num)
        elif unit.startswith('h'): delta += datetime.timedelta(hours=num)
        else: C.log_error(f'unknown adjustment unit: {unit}; ignored.')
        C.log_debug(f'adj: {adj} -> {num=} {unit=} cumulative delta={delta}')

    return start + delta


# ------------------------------ view (web server) ------------------------------

def handler_root(request, hl_index=None, msg=None):
    out = msg if msg else ''
    out += '<p/>\n'

    tab = []
    now = datetime.datetime.now()
    for edc in QUEUE.get_queue_ro():
        atevent = AtEvent(**edc.kwargs)
        delta = edc.fire_dt - now
        when_mins = round(delta.total_seconds() / 60, 1)
        controls = f'<button onclick="window.location.href=\'del?index={atevent.index}\';">del</button>\n'
        idx = f'<b>{atevent.index}</b>' if atevent.index == hl_index else atevent.index
        tab.append([controls, idx, edc.fire_dt, when_mins, atevent.name, atevent.notes[:30], atevent.url[:30], atevent.out ])

    out += H.list_to_table(tab, table_fmt='border="1" cellpadding="5"',
                           header_list=['controls', 'index', 'when', '+mins', 'name', 'notes', 'url', 'send'],
                           title='Queued events')

    if hl_index: out = out.replace(f'<td><b>{hl_index}</b></td>', f'<td bgcolor="yellow"><b>{hl_index}</b></td>')

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

    out += '<p><button onclick="window.location.href=\'.\';">refresh</button>\n'
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

    new_idx = add(url, when, name, out, notes)
    return handler_root(request, new_idx, f'ok: added event {new_idx}')


def handler_del(request):
    index = safe_int(request.get_params.get('index'))
    ok = del_index(index)
    if not ok: return 'delete failed...  <p><a href=".">continue</a></p>'

    return handler_root(request, None, f'ok: deleted index {index}')


def handler_varz(request):
    return W.varz_handler(request, {
        'next_index': NEXT_INDEX,
        'lat_long': f'{LAT} / {LONG}',
        'sunset': str(sunset()),
        'queue_size': len(QUEUE.queue),
        'done_queue_size': len(DONE_QUEUE),
    })

# ========== main

def parse_args(argv):
  ap = C.argparse_epilog()
  ap.add_argument('--debug',    '-d', action='store_true',              help='include debugging info in log')
  ap.add_argument('--filename', '-F', default='atserver_queue.persist', help='filename for persisted queue')
  ap.add_argument('--keep',     '-K', default=4.0, type=float,          help='how long to retain completed items (hours)')
  ap.add_argument('--logfile',  '-L', default='atserver.log',           help='logfile name; use "-" for stdout.')
  ap.add_argument('--port',     '-P', default=8080,                     help='html service port.  0 to disable.')

  g0 = ap.add_argument_group('General event properties')
  g0.add_argument('--default_output',   '-O',  default='err-email:root',  help='default --out option if not provided. nb: only effects items added via web')
  g0.add_argument('--default_retries',  '-R',  default=5,                 help='default --retries option if not provided; nb: only effects items added via web')
  g0.add_argument('--retry_secs',              default=30,                help='how long to wait before retrying (seconds); applies to all events')
  ap.add_argument('--timeout',          '-T',  default=5,                 help='html get timeout (seconds); applies to all events')

  g1 = ap.add_argument_group('Add an event from CLI')
  g1.add_argument('--add',  '-a',  action='store_true', help='add a queued item')
  g1.add_argument('--name', '-n',  default='anonymous', help='name for the item')
  g1.add_argument('--out' , '-o',  default=None,        help='what to do with any output: syslog,file:name,email:dest,err-email:deststdout')
  g1.add_argument('--retries',     default=None,        help='how many times to retry if fails')
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
    C.init_log(sys.argv[0], logfile=ARGS.logfile, filter_level_logfile=C.DEBUG if ARGS.debug else C.INFO)

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
        new_idx = add(ARGS.url, when, ARGS.name, ARGS.out, note)
        print(f'added index {new_idx}')
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

    if ARGS.port: W.WebServer(handlers=HANDLERS).start(port=int(ARGS.port))
    while True:
        QUEUE.check()
        prune_done_queue()
        time.sleep(LOOP_TIME)
        V.bump('check-loops')


if __name__ == '__main__':  sys.exit(main())
