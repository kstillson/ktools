#!/usr/bin/python3
'''TODO: doc
'''

import argparse, os, sys
import view
import kcore.auth as A
import kcore.common as C
import kcore.webserver as W
import ktools.kmc as KMC


WEB_HANDLERS = {
  '/$':         view.root_view,
  '/easy':      view.easy_view,
  '/healthz':   view.healthz_view,
  '/logout':    view.logout_view,
  '/static.*':  view.static_view,
  '/status':    view.status_view,
  '/statusz':   view.statusz_view,
  '/test':      view.test_view,
  '/touchz':    view.touchz_view,
  '/trigger.*': view.trigger_view,
  '/user':      view.user_view,
}


# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description='home automation web server')
  ap.add_argument('--debug', '-d', action='store_true', help='debug mode; log to stdout, disable all external comm')
  ap.add_argument('--kauth-db-filename', '-F', default=A.DEFAULT_DB_FILENAME, help='kauth shared secrets filename')
  ap.add_argument('--kauth-db-password', '-P', default='-', help='kauth shared secrets encryption password.  "-" means query keymanager for "kauth".  Blank disables kauth authN, i.e. clients must use http basic auth when authN required.')
  ap.add_argument('--kauth-max-delta', '-D', type=int, default=A.DEFAULT_MAX_TIME_DELTA, help='max seconds between client and server token times (i.e. replay attack window)')
  ap.add_argument('--kauth-no-ratchet', '-R', action='store_true', help='disable requirement that each kauth request have a later timestamp than the previous one.')  
  ap.add_argument('--logfile', '-l', default='homesec.log', help='filename for operations log.  "-" for stdout, blank to disable log file')
  ap.add_argument('--port', '-p', type=int, default=8080, help='port to listen on')
  ap.add_argument('--syslog', '-s', action='store_true', help='sent alert level log messages to syslog')
  return ap.parse_args(argv)

def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  C.init_log('homesec', '-' if args.debug else args.logfile,
             filter_level_logfile=C.DEBUG if args.debug else C.INFO,
             filter_level_syslog=C.CRITICAL if args.syslog else C.NEVER)

  if args.kauth_db_password == '-': args.kauth_db_password = KMC.query_km('kauth')
  kauth_params = A.VerificationParams(
    db_passwd=args.kauth_db_password, db_filename=args.kauth_db_filename,
    max_time_delta=args.kauth_max_delta, must_be_later_than_last_check=not args.kauth_no_ratchet)
  view.init_kauth(kauth_params)
  
  if args.debug:
    import ext
    ext.DEBUG = True
    view.DEBUG = True
    C.log_warning('** DEBUG MODE ACTIVATED **')
  
  ws = W.WebServer(WEB_HANDLERS, wrap_handlers=not args.debug)
  ws.start(port=args.port, background=False)  # Doesn't return.

  
if __name__ == '__main__':
    sys.exit(main())
