#!/usr/bin/python3
'''Home Service (hs) - web-service for hc (home control) automation system.

'''

import argparse, os, sys

import home_control.hc as HC
import kcore.common as C
import kcore.webserver as W


# ---------- handlers

def hs_control_handler(request):
    items = request.path.split('/')[1:]
    if not items[0].startswith('c') or len(items) < 2: return W.Response('bad control request', 400)
    target = items[1]
    command = items[2] if len(items) > 1 else 'on'
    C.log(f'{target} -> {command}')
    rslt = HC.control(target, command)
    # TODO: need a way to easily determine success/fail and give correct rslt.
    return 'ok: %s' % rslt


def hs_root_handler(request):
    with open('root.html') as f: return f.read()

    
# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description='home automation web server')
  ap.add_argument('--logfile', '-l', default='hs.log', help='filename for operations log.  "-" for stderr, blank to disable log file')
  ap.add_argument('--port', '-p', type=int, default=8080, help='port to listen on')
  ap.add_argument('--syslog', '-s', action='store_true', help='sent alert level log messages to syslog')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])
  
  if args.logfile == '-':
    args.logfile = None
    stderr_level = C.logging.INFO
  else:
    stderr_level = C.logging.NEVER
      
  C.init_log('hs server', args.logfile,
             filter_level_logfile=C.logging.INFO, filter_level_stderr=stderr_level,
             filter_level_syslog=C.logging.CRIT if args.syslog else C.logging.NEVER)
  
  handlers = {
      '/': hs_root_handler,
      '/c.*': hs_control_handler,
  }
  ws = W.WebServer(handlers, wrap_handlers=False)  ##@@ temp
  ws.start(port=args.port, background=False)

  
if __name__ == '__main__':
    sys.exit(main())

