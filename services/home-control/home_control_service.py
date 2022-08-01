#!/usr/bin/python3
'''web-interface for the hc (home control) automation system.

The home_control.hc library (see ../../pylib/home_control) provieds Python
library and command-line interfaces for controlling various smart-home devices
and scenes (i.e. collections of devices and commands for them).  This module
provides a trivial web-interface around that functionality.

The root handler ("/") will serve up the file root.html .  Most of the details
in this file are specific to the details of the author's particular smart-home
setup, as are the contents of ./hcdata_devices.py and ./hcdata_scenes.py.
These files are provided as reference / examples, so you can see how the
devices are defined, arranged into scenes, and then both devices and scenes
are exposed through the HTML presentation.

This module also provides a "/control" handler, which is used by the
javascript of the root.html file for it's operations, but the idea is that
this handler is available to other systems around your network that want to
control smart-home devices (assuming you want to centralize control, rather
than building hc.py into everything that wants to control things).  The
handler takes the simple form "/control/{target}[/{command}]".  Target can be
a device name or a scene name.  If a command isn't provided, "on" is assumed.


SECURITY NOTE: As currently written, this web-server has no authentication
mechanism.  The thought is that when running on a local network, an attacker
could just send commands directly to smart-home units (as they usually also
don't have authN), so adding a authN layer here isn't valuable.  HOWEVER, if
you expose this server beyond your local network, you're giving folks outside
your network the ability to control your stuff.  Make sure to add appropriate
authN in any proxy arrangement you establish that makes this web-server
visible outside a secure local network.

SECURITY NOTE: This web-server uses simplistic and easy-to-guess http GET
params, which makes it vulnerable to cross-site request forgery (CSRF).
Adding local authN wouldn't help.  Adding CSRF tokens would, but this would
significantly complicate the web API for non-human clients -- i.e. the simple
GET-based approach is a valuable feature when the clients are other
reasonably-simple automated systems.  Keep this in mind if you expose this
server outside a trusted local network, even if you've added AuthN in a proxy.
A lot more attention needs to be paid to security before this server should be
allowed to control things more important that a few lights here and there.

'''

import argparse, os, sys

import home_control.hc as HC
import kcore.common as C
import kcore.webserver as W


# ---------- handlers

def hs_control_handler(request):
    try:
        items = request.path.split('/')[2:]   # [0] is "", i.e. lhs of leading '/'.  [1] is "control"
        target = items[0]
        command = items[1] if len(items) > 1 else 'on'
    except:
        return W.Response('correct path looks like /control/target[/command].', 400)
    ok, rslt = HC.control(target, command)
    C.log(f'({target},{command}) -> ok={ok}: {rslt}', C.INFO if ok else C.ERROR)
    return f'{"ok" if ok else "ERROR"}: {rslt}'


def hs_c_handler(request):
    target = request.get_params.get('target')
    if not target: target = request.get_params.get('t')
    if not target: target = request.get_params.get('d')
    if not target: return W.Response('must pass "target" or "t" as get param.', 400)
    command = request.get_params.get('command')
    if not command: command = request.get_params.get('c')
    if not command: command = request.get_params.get('v')
    if not command: command = 'on'

    ok, rslt = HC.control(target, command)
    C.log(f'({target},{command}) -> ok={ok}: {rslt}', C.INFO if ok else C.ERROR)
    return f'{"ok" if ok else "ERROR"}: {rslt}'


def hs_robots_handler(request):
    # We have state-changing GET requests; disallow robots from exploring our links.
    return 'User-agent: *\nDisallow: /\n'


def hs_root_handler(request):
    with open('root.html') as f: return f.read()

    
# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description='home automation web server')
  ap.add_argument('--debug', '-d', action='store_true', help='put home_control into debug mode')
  ap.add_argument('--logfile', '-l', default='hs.log', help='filename for operations log.  "-" for stderr, blank to disable log file')
  ap.add_argument('--port', '-p', type=int, default=8080, help='port to listen on')
  ap.add_argument('--syslog', '-s', action='store_true', help='send error level log messages to syslog')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])
  
  C.init_log('hs server', args.logfile,
             filter_level_logfile=C.INFO,
             filter_level_stderr=C.DEBUG if args.debug else C.NEVER,
             filter_level_syslog=C.ERROR if args.syslog else C.NEVER)

  if args.debug: HC.control('doesnt', 'matter', {'debug': True})
  
  handlers = {
      '/': hs_root_handler,
      '/control/.*': hs_control_handler,
      '/c.*': hs_c_handler,
      '/robots.txt': hs_robots_handler,      
  }
  ws = W.WebServer(handlers)
  ws.start(port=args.port, background=False)  # Doesn't return.

  
if __name__ == '__main__':
    sys.exit(main())

