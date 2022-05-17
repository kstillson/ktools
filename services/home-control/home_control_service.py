#!/usr/bin/python3
'''Home Service (hs) - web-service for hc (home control) automation system.

TODO: more doc

GUI (root.html): /
send on-demand control:   /control/{target}[/{command}]


TODO: add robots.txt (perhaps default handler...?)

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
    C.log(f'({target},{command}) -> ok={ok}: {rslt}')
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
    C.log(f'({target},{command}) -> ok={ok}: {rslt}')
    return f'{"ok" if ok else "ERROR"}: {rslt}'


def hs_root_handler(request):
    with open('root.html') as f: return f.read()

    
# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description='home automation web server')
  ap.add_argument('--debug', '-d', action='store_true', help='put home_control into debug mode')
  ap.add_argument('--logfile', '-l', default='hs.log', help='filename for operations log.  "-" for stderr, blank to disable log file')
  ap.add_argument('--port', '-p', type=int, default=8080, help='port to listen on')
  ap.add_argument('--syslog', '-s', action='store_true', help='sent alert level log messages to syslog')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])
  
  C.init_log('hs server', args.logfile,
             filter_level_logfile=C.INFO, filter_level_stderr=stderr_level,
             filter_level_syslog=C.CRITICAL if args.syslog else C.NEVER)

  if args.debug: HC.control('doesnt', 'matter', {'debug': True})
  
  handlers = {
      '/': hs_root_handler,
      '/control/.*': hs_control_handler,
      '/c.*': hs_c_handler,
  }
  ws = W.WebServer(handlers)
  ws.start(port=args.port, background=False)  # Doesn't return.

  
if __name__ == '__main__':
    sys.exit(main())

