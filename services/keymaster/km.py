#!/usr/bin/python3
'''Key Master (km) - local network secret bootstrapper.

This is a web-server that hosts a small database of secrets.  Clients request
secrets by providing the name of the secret they want via an https GET
request.

Clients are authenticated using kcore.auth.py tokens, which include a private
client-machine unique identifier and an optional username/password.  That is,
each keymaster secret is associated with a kcore.auth "shared secret" (shared
between the client machine and the keymaster server), and that secret is
hardware-locked to the machine on which it was generated, which should be the
machine that km requests are going to come from.

The km secrets database is stored in a symmetrically encypted GPG file, and
the server does not know the password to it.  This makes it safe to backup the
source directory without exposing secrets (although see notes below concerning
the security of the TLS private key).

To enable the server (i.e. decrypt the database), the service owner must
manually provide the GPG passphrase via a web client (a login-style form is
provided).  Once this is done, the service is up and can serve secrets.

The intended use for KM is services that require some sort of password in
order to initialize, but where you do not wish to build the password into the
service.  On startup, a service can contact the key-master and request its own
secrets.  Clients should be smart enough to auto-retry secret retieval,
in-case they contact the key-master at a time when the database has not yet
been unlocked.  A suitable client (both Python library and command-line) is
in tools_for_users/kmc.py

The vision is that in the event of a many-service restart, all the systems
that need secerts will go into retry loops until key-master admin enters the
one master password to unlock the KM database, and then all the services can
auto-restart without further intervention.

In addition to kcore.auth tokens, KM also checks the requesting client's
source-IP address.  If you don't want this, override the hostname with "*"
when registering a secret.  Make sure to do this on the client side when
generating the key registration (kmc.py -g ...), and when retrieving secrets,
as the hostname is mixed-in to the kcore.auth shared-secret generation.  Also
note that while a hostname of "*" disables source-ip checking, a kcore.auth
shared secret still has machine-specific data mixed in, and so by default will
only work for key retireval requests generated from the same machine as where
the key registration was generated.

If you really want to be able to retrieve a secret from multiple different
client machines, you'll need to set the $PUID environment variable to some
fixed-and-secret value (one that is unique to this key) both when generating
the key registration and when retrieving the secret.

By default, the server is deliberately hyper-sentitive, meaning that a single
unauthorized or not-understood request will cause the server to panic and
clear it's decrypted copy of the database.  The key-master owner must then
re-enter the GPG passphrase before any more secrets can be served.  This is
intended to discourage hacking or experimentation against the server.  It also
means you probably need to continuously monitor the KM; see the /healthz
handler for an easy way to do that.  If you don't want the hyper-sensitive
mode, for example in cases where curious or malicious network users might
cause a denial-of-service by panicing the server, use the --dont-panic flag to
turn it off.

TODO: under some circumstances (e.g. cert verification failure),
requests.get() can retry multiple times in quick succession.  Currently that
will cause the server to panic and lock-down.  Should we make a
LAST_RECEIVED_TIMES ratchet failure non-panicing?  Problem is that this makes
real replay attacks non-panicing...  hmmm...

The secrets database is formatted as a Python serialized @dataclass.  See
km-test.data.gpg for an example; the passphrase is "test123".  btw, that file
was generated with $PUID="test".  Note that various tests are dependent on
this file's current contents, so you might break them if you change it.  Your
real secrets database goes in private.d/km.data.gpg.

'''

import argparse, getpass, os, sys
from dataclasses import dataclass

import kcore.auth as A
import kcore.common as C
import kcore.uncommon as UC
import kcore.varz as V
import kcore.webserver as W


# ---------- the secrets database

@dataclass
class Secret:
    keyname: str
    secret: str
    kauth_secret: str
    comment: str = None
    override_expected_client_addr: str = None


class Secrets(UC.DictOfDataclasses):
    def ready(self): return len(self) > 0

    def reset(self):
        self.clear()
        C.log('RESET: keys cleared')
        V.bump('resets')
        V.set('loaded-keys', 0)

    def load_from_gpg_file(self, filename, password):
        with open(filename) as f: crypted = f.read()
        resp = self.from_string(UC.gpg_symmetric(crypted, password), Secret)
        V.set('loaded-keys', len(self))
        return resp

            
# ---------- global state

ARGS = {}
SECRETS = Secrets()

# ---------- helpers

def ouch(user_msg, log_msg, varz_name):
    if varz_name: V.bump(varz_name)
    if 'Time difference' in log_msg:
        # Time delta errors seem common; not sure why. Make them non-panic'ing for now.
        V.bump('keyfail-timedelta')
        C.log_error(log_msg)
    elif 'token is not later than a previous token' in log_msg:
        # Multiple quick key retrieval attempts also seem common; because of automatic retries in the client's "requests" call.  Also make them non-panic'ing for now.
        V.bump('keyfail-timedelta')
        C.log_error(log_msg)
    elif ARGS.dont_panic:
        V.bump('dont-panic')
        C.log_error(log_msg)
    else:
        V.bump('panic')
        SECRETS.reset()
        C.log_alert(log_msg)
    return W.Response(f'ERROR: {user_msg}', 403)


# ---------- handlers

def km_healthz_handler(request):
    return 'ok' if SECRETS.ready() else 'error- not ready; need password.'
    
    
def km_load_handler(request):
    SECRETS.reset()
    SECRETS.load_from_gpg_file(ARGS.datafile, request.post_params.get('password'))
    if not SECRETS.ready():
        C.log_alert('incorrect password received for key manager load request')
        V.bump('reloads-fails')
        return 'error'
    V.bump('reloads-ok')
    C.log('LOADED KEYS OK- READY')
    return 'ok'


def km_reset_handler(request):
    if ARGS.dont_panic: return 'Server in stability mode; cannot reset from remote.'
    C.log_alert('km database cleared by GET request')
    SECRETS.reset()
    return 'zapped'


def km_root_handler(request):
    if SECRETS.ready():
        C.log_error('keymanager root page access; probe?')
        return 'hi'
    return '<html><body><form action="/load" name="loader" method="post">\n password: <input type="password" name="password">\n <input type="submit" value="Submit">\n</form>\n</body>\n</html>\n'


def km_default_handler(request):
    if not SECRETS.ready():
        C.log('keyfail-notready')
        V.bump('keyfail-notready')
        return W.Response('not ready', 503)
    full_keyname = request.path[1:]  # trim leading /
    token = request.get_params.get('a')

    secret = SECRETS.get(full_keyname)
    if not secret:
        return ouch('no such key', f'attempt to get non-existent key: {full_keyname}', 'keyfail-notfound')

    client_addr = request.remote_address.split(':')[0]

    okay, status, hostname, username, sent_time = A.validate_token_given_shared_secret(
        token=token, command=full_keyname, shared_secret=secret.kauth_secret,
        client_addr=client_addr,
        override_expected_client_addr=secret.override_expected_client_addr,
        must_be_later_than_last_check=not ARGS.noratchet,
        max_time_delta=ARGS.window)
    if not okay:
        return ouch(status, f'unsuccessful key retrieval attempt full_keyname={full_keyname}, req_hostname={hostname}, client_addr={client_addr}, username={username}, status={status}',
                    'keyfail-hostname' if 'hostname' in status else 'keyfail-kauth')
    
    C.log(f'successful key retrieval: full_keyname={full_keyname} client_addr={client_addr} username={username}')
    V.bump('key-success')
    return secret.secret

            
# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description='key manager server')
  ap.add_argument('--certkeyfile', '-k', default='keymaster.pem', help='name of file with both server TLS key and matching certificate.  set to blank to serve http rather than https (NOT RECOMMENDED!)')
  ap.add_argument('--datafile', '-d', default='km.data.gpg', help='name of encrypted file with secrets database')
  ap.add_argument('--dont-panic', action='store_true', help='By default the server will panic (i.e. clear its decrypted secrets database) if just about anything unexpected happens, including any denied request for a key.  This flag disables that, favoring stability over pananoia.')
  ap.add_argument('--logfile', '-l', default='km.log', help='filename for operations log.  "-" for stderr, blank to disable log file')
  ap.add_argument('--port', '-p', type=int, default=4444, help='port to listen on')
  ap.add_argument('--noratchet', '-R', action='store_true', help='By default each request for a key must come after the last successful request for that key; this prevents request replay attacks.  It also limits key retrievals to one-per-second (for each key).  This disables that limit, and relies just on --window to prevent replay attacks.')
  ap.add_argument('--syslog', '-s', action='store_true', help='sent alert level log messages to syslog')
  ap.add_argument('--window', '-w', type=int, default=90, help='max seconds time difference between client key request and server receipt (i.e. max clock skew between clients and servers).  Set to 0 for "unlimited".')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  global ARGS
  ARGS = args  # easy communication to things like the handlers.

  if args.logfile == '-':
    args.logfile = None
    stderr_level = C.INFO
  else:
    stderr_level = C.NEVER
      
  C.init_log('km server', args.logfile,
             filter_level_logfile=C.INFO, filter_level_stderr=stderr_level,
             filter_level_syslog=C.CRITICAL if args.syslog else C.NEVER)
  
  handlers = {
      '/healthz':      km_healthz_handler,
      '/load':         km_load_handler,
      '/qqq':          km_reset_handler,
      '/quitquitquit': km_reset_handler,
      '/T': lambda r:  str(vars(SECRETS)),
      '/':             km_root_handler,
      None:            km_default_handler,
  }
  ws = W.WebServer(handlers)
  
  ws.start(port=args.port, background=False,
           tls_cert_file=args.certkeyfile, tls_key_file=args.certkeyfile)

  
if __name__ == '__main__':
    sys.exit(main())

