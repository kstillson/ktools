#!/usr/bin/python3
'''command-line and py-library client for the keymaster service

See services/keymaster/km.py for details on the service we talk to.

This module uses kcore/auth.py for authentication.  As such, usernames and
passwords are not required in cases where the client is a single-tenant
machine, but keep in mind the client registration must be done on the same
machine as where the key requests will be generated, as machine-specific
details are encoded into the registration.
'''

import argparse, os, random, requests, socket, sys, time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import kcore.auth
import kcore.common as C


# ---------- global settings

DEBUG = False   # warning: outputs lots of secrets to stderr.


# ---------- general helpers

def find_cert(filename):
  if os.path.exists(filename): return os.path.abspath(filename)
  candidate = os.path.join(os.path.dirname(__file__), filename)
  if os.path.exists(candidate): return candidate
  candidate = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
  if os.path.exists(candidate): return candidate
  return None


# ---------- key request API (run on the km client)


def query_km(keyname,
             keyname_prefix='%h-',
             override_hostname=None, username='', password='',
             km_host_port='keys:4444', km_cert='keymaster.crt',
             timeout=5, retry_limit=None, retry_delay=15):
  '''query the keymaster for a key

  Traditionally keymaster uses full keynames prefixed by the hostname of the
  client that owns/retrieves the key, followed by a dash, i.e. [hostname-keyname]
  Change keyname_prefix if you don't want this.

  Set km_cert to None to disable TLS (i.e. use http). Not recommended for
  transferring secrets!!  Set km_cert to '' to use TLS but not validate the
  server side certificate.  This opens you up to man-in-the-middle attacks, but
  might be ok on trusted networks.

  retry_limit=None will retry forever.  Set to 0 to disables retries.  Remember
  that the keymaster needs to be manually initialized before it can serve keys,
  so retrying for a long time is a good idea.

  If a key was registered with override_hostname='*', you must also provide that
  parameter here.  This special value has the side-effect of disabling
  server-side source-IP checking.

  Returns the retrieved secret/key (as a string), or None upon failure.
  '''
  hostname = override_hostname or socket.gethostname()

  if keyname_prefix is None: keyname_prefix = ''
  full_keyname = keyname_prefix.replace('%h', hostname) + keyname

  if km_cert:
    verify = find_cert(km_cert)
    if not verify: C.log_error('unable to find certificate %s' % km_cert)
  else: # km_cert is either '' (tls but don't verify) or None (no tls).
    verify = False

  retry = 0
  while retry_limit is None or retry <= retry_limit:
    if retry > 0: time.sleep(retry_delay)

    # token generation must occur within retry loop, as it's time dependent.
    authn_token = kcore.auth.generate_token(full_keyname, hostname, username, password)
    if DEBUG: print(f'DEBUG: query_km token regeneration: full_keyname={full_keyname} hostname={hostname} username={username} password={password} PUID={os.environ.get("PUID")} authn_token={authn_token}', file=sys.stderr)

    protocol = 'http' if km_cert is None else 'https'
    url = '%s://%s/%s?a=%s' % (protocol, km_host_port, full_keyname, authn_token)
    if not verify: requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    try:
      resp = requests.get(url, timeout=timeout, verify=verify)
      if resp.status_code == 200 and resp.text and not 'ERROR' in resp.text: return resp.text

      err = 'ERROR: status %d (%s)' % (resp.status_code, resp.text)

    except Exception as e:
        err = 'ERROR: %s' % e
    C.log_error(err)
    retry += 1

  C.log_error('out of retries; giving up.')
  return err  # return most recent error code


# ---------- main for CLI

def parse_args(argv):
  ap = argparse.ArgumentParser(description='keymanager client')
  ap.add_argument('--username', '-u', default='', help='when using multiple-users per machine, this specifies which username to generate a registration for.  These do not need to match Linux usernames, they are arbitrary strings.')
  ap.add_argument('--password', '-p', default='', help='when using multiple-users per machine, this secret identifies a particular user')
  ap.add_argument('--password-env', '-e', default='', help='name of environment variable with password')
  ap.add_argument('--hostname', '-H', default=None, help='hostname to generate/save registration for.  Defaults to system hostname.  If retrieving an "any host" key, must be set to "*"')
  ap.add_argument('--prefix', '-P', default='%h-', help='prefix for key name. Defaults to "%%h-", which prefixes the hostname, and is usually what you want.')
  ap.add_argument('keyname', default=None, help='name of the key to retrieve/create')

  group1 = ap.add_argument_group('advanced', 'advanced settings for key retrival')
  group1.add_argument('--km-host-port', default='keys:4444', help='hostname:port for keymaster to contact')
  group1.add_argument('--km_cert', default='keymaster.crt', help='filename of cert to use for km server TLS checks, or "" to use unvalidated TLS, or "-" to use HTTP without TLS.')
  group1.add_argument('--timeout', default=5, type=int, help='seconds for external connect timeouts')
  group1.add_argument('--retry-limit', default=None, type=int, help='how many times to retry.  Leave unset for "infinite"')
  group1.add_argument('--retry-delay', default=5, type=int, help='seconds to wait between retries')

  group2 = ap.add_argument_group('special', 'alternate run modes')
  group2.add_argument('--extract-machine-secret', '-E', action='store_true', help='output the machine-unique-private data and stop.  Allows you to run key registations on the km server by transporting this value to the server (rather than a fully-formed key registration from "-g").')

  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  if args.extract_machine_secret:
    print(kcore.auth.get_machine_private_data())
    return 0

  if not args.keyname: sys.exit('need to provide a keyname to retrieve')

  if args.password_env:
      args.password = os.environ.get(args.password_env)
      if not args.password: sys.exit('--password-env flag used, but $%s is not set.' % args.password_env)

  if args.km_cert == '-': args.km_cert = None

  secret = query_km(keyname=args.keyname, keyname_prefix=args.prefix,
                    override_hostname=args.hostname, username=args.username, password=args.password,
                    km_host_port=args.km_host_port, km_cert=args.km_cert,
                    timeout=args.timeout, retry_limit=args.retry_limit, retry_delay=args.retry_delay)
  if not secret: return 1
  print(secret)
  return 0


if __name__ == '__main__':
    sys.exit(main())
