#!/usr/bin/python3

'''Web-based gift coordination system

WARNING: This system has no thought whatsoever to security.  Users can "login"
just by saying who they are (i.e. no passwords), and the whole URL and session
management schemes are doubtless full of vulnerabilities.  This is intended to
only manage very low value data, and to be run in a highly isolated
environment.  Specifically- please run this inside a container that does
nothing else, and it's recommended that any visibility to the Internet be
proxied by a server that requires some independent layer of authentication
(e.g. http basic auth).

This is a quick-and-dirty tool my family uses to share ideas for
Christmas/birthday gifts, and to try to avoid duplicate gift purchases.

Any family member can log in, and enter gift ideas for themselves or for
anyone else.  By default, the system won't show users gifts targeted to
themselves, or gifts to anyone that are marked as taken (although these
filters can be overriden on the login screen).

TODO(defer): add an event field so Christmas, birthday, and perhaps "other"
gift ideas can be separated.

TODO(defer): add an ability to filter by year, so old data can be retained but not shown by default.

NOTE: when ideas are "deleted," they are actually only marked as deleted; the
data is actually retained.  This is because I got sufficient requests to
"undo" deletions, that I figured I'd make it easier to do this.  
TODO(defer): add a CLI flag to purge deleted items.
TODO(defer): add a UI option to actually delete and/or to un-delete.

TODO(defer): Add some tests...?

'''

import argparse, os, sys
import view
import kcore.common as C
import kcore.webserver as W


WEB_HANDLERS = {
  '/$':         view.root_view,
  '/add':       view.add_view,
  '/edit':      view.edit_view,
  '/export':    view.export_view,
  '/healthz':   view.healthz_view,
  '/hold':      view.hold_view,
  '/login':     view.login_view,
  '/logout':    view.logout_view,
  '/take':      view.take_view,
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

  C.init_log('gift_coord', '-' if args.debug else args.logfile,
             filter_level_logfile=C.DEBUG if args.debug else C.INFO,
             filter_level_syslog=C.CRITICAL if args.syslog else C.NEVER)

  if args.debug:
    view.DEBUG = True
    C.log_warning('** DEBUG MODE ACTIVATED **')
    
  ws = W.WebServer(WEB_HANDLERS, wrap_handlers=not args.debug)
  ws.start(port=args.port, background=False)  # Doesn't return.

  
if __name__ == '__main__':
    sys.exit(main())
