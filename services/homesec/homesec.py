#!/usr/bin/python3
'''home security system

For the academically inclined, homesec is a simple FSM (finite state machine)
implemented using the MVC (model-view-controller) paradygm.  Translation follows...

homesec supports a number of "partitions."  You can think of these as somewhat
independent security system instances, each with their own "state" (armed,
disarmed, etc).  For example, I have a "default" partition which consists of
the doors, windows, motion sensors, around the house, and a "safe" partition,
which involves a sensor that detects when the vault that stores my valuables
is open.  I might want to relax the "default" partition because myself and
guests are over and would be setting off sensors all over the place, but leave
the "safe" partition armed, because no-one is expected to be digging around in
the vault at that time.

The states can be anything, but I've provided what I believe are a useful set
of them.  The standard states a user might set are:
  disarmed, arm-away, arm-home, arm-auto, and panic

There are also a bunch of internal states:
  alarm-triggered, alarm, and test-mode

The partitions transition between states when homesec receives "triggers,"
which are just web-requests to the /trigger handler.  There is a data table
called the TRIGGER_RULES, which basically says "if you're in state X and
receieve trigger Y, then take action Z."  There's a bunch of actions that are
supported, like transitioning a partition to a different state, or sending a
request to a voice synthesizer to make an announcement, etc.

There is also a STATE_RULES table, which gives actions to take whenever
particular states are entered or exited.  So for example, when the "alarm"
state is entered, it sends requests to the smart-home system to turn on lights
and sirens, and then the "alarm" stte is left, it turns them off again.

TODO(doc) @@

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

  if args.kauth_db_password == '-':
    args.kauth_db_password = KMC.query_km('kauth')
    if args.kauth_db_password.startswith('ERROR'): C.log_critical('unable to retrieve kauth password')
    else: C.log('successfully retrieved kauth password')
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
