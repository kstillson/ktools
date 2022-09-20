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
and sirens, and then the "alarm" state is left, turns them off again.

One other important table is TRIGGER_LOOKUPS.  Not every trigger has a lookup,
but the ones that do can set a bunch of useful parameters:
 - zone: triggers can be grouped into arbitrary zones, such as "inside" or "outside",
   and then TRIGGER_RULES can be based on the zone rather than the individual trigger.
   This is basically just to simplify the TRIGGER_RULES.
 - partition: some sensors are associated with a particular partition.  For example,
   the opening sensor on my vault is assocated with the 'safe' partition, whereas all
   others a 'default'.
 - tardy_time: intended to provide a "is the battery dead?" warning for sensors that
   are reliably activated regualrly (e.g. indoor motion sensors).  If the trigger has
   not been seen within this many seconds, the trigger is considered 'tardy,' and
   the /healthz handler will start to report an error.
 - squelch_time: for triggers that stutter (e.g. flaky switches that send several
   signals in a row when activated), or cases like doors that, once opened may be
   used several times during the next few minutes, and you don't really need to be
   separately told about each opening.  A trigger with a squelch time will ignore
   repeated/duplicate trigger for this many seconds after one that is processed.
 - friendly_name: this becomes available as a parameter to trigger and state
   rules, and is useful when generate speech synthesis which contains a reference
   to which trigger fired, and a more human-friendly name is desired.

About arm-auto: This is a state that dynamically selects between arm-home and
arm-away based on how many people are home.  For example, when I leave, I push
a "Ken is leaving" button, which sends /trigger/touch-away-delay/ken.  After a
few seconds, this marks "ken" as "away".  When I return, I enter my code into
a keypad, which results in sending /trigger/touch-home/ken.  Now I'm home.  My
house-mate also has their own 'leaving' button and 'returning' keypad code.
If anyone is marked as 'home', then 'arm-auto' resolves to 'arm-home'.
If no-one is marked as 'home', then 'arm-auto' resolves to 'arm-away'.

Authentication is requred for web handlers that can change system state, for
example /trigger's.  homesec supports two different authN mechanisms:
 - For humans, http basic auth is supported, using username/password combinations
   in the USER_LOGINS dict.
 - For automated systems (e.g. sensors), the kcore.auth system is used.
   This does require a little bit of work to create and register the shared secrets;
   see ../../pylib/kcore/auth.py for details.

homesec.py: This file contains the system 'main', but doesn't actually do much
  except initialize things and pass control to the web-server.

view.py: The view contains the external user interface, which in this case means
  the handlers for the web-server and the authentication logic.  Like all
  kcore.webserver handlers, these take in kcore.webserver.Request objects and
  return HTML.  There's also a trivial template system in the render() function.

controller.py: This is where all the 'business logic' happens.  There are a
  bunch of supporting functions, but the main two are run_trigger(), which is
  run by view.trigger_view() when a trigger is received, adds all sorts of
  tracking metadata, figures out which action is going to be taken, and then
  calls the other major function: take_action().

  It's worth noting that run_trigger() receives the kcore.webserver.Request
  object from the view (converted into dict form), copies it to a new dict
  named "tracking", and adds all its metadata to that.  "tracking" is then
  extensively passed around within the controller.  So this dict contains all
  the data the webserver provided (e.g. the key 'user', if the connection
  was authenticated), and adds all the controller-specific fields you see in
  run_trigger().

model.py: The model is basically an abstraction layer that translates between
  the things that the view and the controller need to know/do with data, and
  the details of the data storage mechanism (which is in data.py).  In other
  words, the methods in model.py are in the "universe of discourse" of the
  view and controller, so it has requests like get_all_touches() or
  get_friendly_touches().  data.py is structured in a way that makes sense to
  efficiently store/retrieve the data, and model.py translates between these.

data.py: This is where the data actually lives.  For the most-part, the data
  is just Python dict's or lists, generally of @dataclass's (which are also
  defined in data.py).  Originally I had all this stuff in a mysql database,
  but I eventually decided it's just easier to have it as nice simple
  hard-coded Python data-structures.  It does mean you have to restart the
  system if you change things, but I'm as happy to consider that a security
  feature as a bother.  There is also some data that needs to change
  dynamically and persist between restarts(/crashes).  Specifically: the
  current state of each partition, and the last-touch data (which stores the
  last time each trigger was seen, to support squlech and tardy calculations,
  and the marks for which users are 'home' and 'away' for 'auto-arm' mode).
  This 'dynamic' data is stored in a simple serialized format that is easily
  human readable/editable, and stored in simple text files.  Again, this is
  just so much easier to deal with than setting up and maintaining a database,
  and then trying to deal with migrations and separate access control for it..

ext.py: There are several cases where the controller needs to take actions
  that involve reaching outside the homesec system: sending speech synthesis
  "announcement" requests, sending push notifications, sending emails,
  controlling lights / sirens, etc.  All of that is gathered here.
  NOTE: many of the details in the provided file are specific to the author's
  home system.  Use this as a reference/example, but you'll doubtless need to
  make changes to inegrate with your own systems.

private.d/: Various details of both data.py and ext.py are site specific and
  private (for example, while I'm willing to provide lots of examples, I'm not
  willing to show you my USER_LOGINS dict, even if the passwords are hashed.)
  So both use kcore.uncommon.load_file_into_module(), which allows you to
  create files with the same names (e.g. private.d/data.py), and anything you
  put in there will override what's in ./data.py.  The top-level .gitignore
  file makes sure that nothing in a private.d/ subdirectory makes its way into
  git.

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
  ap.add_argument('--syslog', '-s', action='store_true', help='send critical log messages to syslog')
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
