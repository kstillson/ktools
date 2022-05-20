#!/usr/bin/python3
'''TODO: doc
'''

import argparse, os, sys
import view
import kcore.common as C
import kcore.webserver as W


WEB_HANDLERS = {
    '/$':         view.root_view,
    '/easy':      view.easy_view,
    '/healthz':   view.healthz_view,
    '/static.*':  view.static_view,
    '/status':    view.status_view,
    '/statusz':   view.statusz_view,
    '/touchz':    view.touchz_view,
    '/trigger.*': view.trigger_view,
}


# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description='home automation web server')
  ap.add_argument('--debug', '-d', action='store_true', help='debug mode; log to stdout, disable all external comm')
  ap.add_argument('--logfile', '-l', default='homesec.log', help='filename for operations log.  "-" for stdout, blank to disable log file')
  ap.add_argument('--port', '-p', type=int, default=8080, help='port to listen on')
  ap.add_argument('--syslog', '-s', action='store_true', help='sent alert level log messages to syslog')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  C.init_log('homesec', '-' if args.debug else args.logfile,
             filter_level_logfile=C.DEBUG if args.debug else C.INFO,
             filter_level_syslog=C.CRITICAL if args.syslog else C.NEVER)

  if args.debug:
    import ext
    ext.DEBUG = True
    view.DEBUG = True
    C.log_warning('** DEBUG MODE ACTIVATED **')
  
  ws = W.WebServer(WEB_HANDLERS, wrap_handlers=not args.debug)
  ws.start(port=args.port, background=False)  # Doesn't return.

  
if __name__ == '__main__':
    sys.exit(main())
