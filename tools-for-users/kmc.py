#!/usr/bin/python3
'''command-line and py-library client for the keymaster service

See services/keymaster/km.py for details on the service we talk to.

This module uses pylib/k_auth.py for authentication.  As such, usernames and
passwords are not required in cases where the client is a single-tenant
machine, but keep in mind the client registration must be done on the same
machine as where the key requests will be generated, as machine-specific
details are encoded into the registration.

'''

import argparse, os, random, requests, socket, sys, time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import k_auth

# ---------- key request API (run on the km client)

'''query the keymaster for a key

Traditionally keymaster uses full keynames prefixed by the hostname of the
client that owns/retrieves the key, followed by a dash, i.e. [hostname-keyname]
Change keyname_prefix if you don't want this.

Set km_cert to None to disable TLS (i.e. use http). Not recommended for
transferring secrets!!  Set km_cert to blank to use TLS but not validate the
server side certificate.  This opens you up to man-in-the-middle attacks, but
might be ok on trusted networks.

retry_limit=None will retry forever.  Set to 0 to disables retries.  Remember
that the keymaster needs to be manually initialized before it serves keys, so
retrying for a long time is a good idea.

If a key was registered with override_hostname='*', you must also provide that
parameter here.  This special value has the side-effect of disabling
server-side client host identity checking.

Returns the retrieved secret/key (as a string), or None upon failure.
'''

def query_km(keyname,
             keyname_prefix='%h-',
             override_hostname=None, username='', password='',
             km_host_port='km:4443', km_cert='km.crt',
             timeout=5, retry_limit=None, retry_delay=5, errors_to=sys.stderr):

  hostname = override_hostname or socket.gethostname()
  if hostname == '*': os.environ['PUID'] = '*'

  if keyname_prefix is None: keyname_prefix = ''
  full_keyname = keyname_prefix.replace('%h', hostname) + keyname

  authn_token = k_auth.generate_token(full_keyname, hostname, username, password)

  protocol = 'http' if km_cert is None else 'https'
  url = '%s://%s/%s?a=%s' % (protocol, km_host_port, full_keyname, authn_token)
  verify = km_cert or False
  if not verify: requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

  retry = 0
  while retry_limit is None or retry <= retry_limit:
    try:
      resp = requests.get(url, timeout=timeout, verify=verify)
      if resp.status_code == 200: return resp.text
      err = 'status %d (%s)' % (resp.status_code, resp.text)
    except Exception as e:
        err = 'error: %s' % e
    if errors_to: print(err, file=errors_to)
    retry += 1
    time.sleep(retry_delay)

  if errors_to: print('out of retries; giving up.', file=errors_to)
  return None


# ---------- key generation API (run on the km client or with $PUID set)

# Set override_hostname to '*' to allow key retireval from any host.
# Note that keys with hostname '*' and no password are completely unprotected.

def generate_key_registration(
        keyname, keyname_prefix='%h-',
        key = None,
        override_hostname=None, username='', password=''):

  hostname = override_hostname or socket.gethostname()
  if hostname == '*': os.environ['PUID'] = '*'

  if keyname_prefix is None: keyname_prefix = ''
  full_keyname = keyname_prefix.replace('%h', hostname) + keyname

  authn_reg = k_auth.generate_client_registration(hostname, username, password)

  if not key:
    key = ''.join(random.choice(string.ascii_letters) for i in range(20))

  return '[%s]\nsecret=%s\nhost=%s\nauthn=%s\n' % (full_keyname, key, hostname, authn_reg)


# ---------- main for CLI

def main(argv):
  ap = argparse.ArgumentParser(description='keymanager client')
  ap.add_argument('--username', '-u', default='', help='when using multiple-users per machine, this specifies which username to generate a registration for.  These do not need to match Linux usernames, they are arbitrary strings.')
  ap.add_argument('--password', '-p', default='', help='when using multiple-users per machine, this secret identifies a particular user')
  ap.add_argument('--password-env', '-e', default='', help='name of environment variable with password')
  ap.add_argument('--hostname', '-H', default=None, help='hostname to generate/save registration for.  Defaults to system hostname.  If retrieving an "any host" key, must be set to "*"')
  ap.add_argument('--prefix', '-P', default='%h-', help='prefix for key name. Defaults to "hostname=", which is usually what you want.')
  ap.add_argument('keyname', default=None, help='name of the key to retrieve/create')

  group1 = ap.add_argument_group('advanced', 'advanced settings for key retrival')
  group1.add_argument('--km-host-port', default='km:4443', help='hostname:port for keymaster to contact')
  group1.add_argument('--km_cert', default='km.crt', help='filename of cert to use for km server TLS checks, or "" to use unvalidated TLS, or "-" to use HTTP without TLS.')
  group1.add_argument('--timeout', default=5, type=int, help='seconds for external connect timeouts')
  group1.add_argument('--retry-limit', default=None, type=int, help='how many times to retry.  Leave unset for "infinite"')
  group1.add_argument('--retry-delay', default=5, type=int, help='seconds to wait between retries')

  group2 = ap.add_argument_group('special', 'alternate modes associated with key/secret registration, rather than retrieval')
  group2.add_argument('--generate-secret-registration', '-g', metavar='SECRET', default=None, help='generate and output a keymaster registration for the specified secret.  You will need to copy this over to the km server and add it to the encrypted database file.')
  group2.add_argument('--extract-machine-secret', '-E', action='store_true', help='output the machine-unique-private data and stop.  Allows you to run key registations on the km server by manually transporting this value to the server.')

  args = ap.parse_args(argv)

  if args.extract_machine_secret:
    print(k_auth.get_machine_private_data())
    return 0

  if not args.keyname: sys.exit('need to provide a keyname to operate on')

  if args.password_env:
      args.password = os.environ.get(args.password_env)
      if not args.password: sys.exit('--password-env flag used, but $%s is not set.' % args.password_env)

  if args.generate_secret_registration:
    print(generate_key_registration(args.keyname, args.prefix, args.generate_secret_registration, args.hostname, args.username, args.password))
    return 0

  # Looks like we're doing a key retrieval.
  if args.km_cert == '-': args.km_cert = None

  print(query_km(args.keyname, args.prefix,
                 args.hostname, args.usename, args.password,
                 args.km_host_port, args.km_cert,
                 args.timeout, args.retry_limit, args.retry_delay))

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
