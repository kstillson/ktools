#!/usr/bin/python3
'''A client-machine-locked shared-secret authentication token generator.

Inputs:
  - a string (e.g. a command to run on a server after authentication)
  - (optionally) a username
  - (optionally) a user password

Implicid inputs:
  - a piece of private unique data extracted from the client machine's hardware
  - the current time

Output:
  - a string that ties all the above together into an authN token.

                  --------------------------------

An example session using the command-line interface:

>> On the client machine, we generate a machine+user+password secret:
./k_auth.py -g -u user1 -p pass1
v2:blue2:user1:09670f2945f669119074

>> (you can see the client hostname of 'blue2' was autodetected)

>> On the server, we register that secret:
./k_auth.py -r v2:blue2:user1:09670f2945f669119074
Done.  Secrets file now has 1 entries.

>> Now on the client, we generate a token that authenticates a command:
./k_auth.py -c 'command1' -u user1 -p pass1
v2:blue2:user1:1648098230:b59d4ab53f035815c689

>> and finally, on the server, we validate the token for that command:
./k_auth.py -v v2:blue2:user1:1648098230:b59d4ab53f035815c689 -c 'command1' -u user1 -H blue2
validated? True

Desirable properties:
- a change to any of the data will cause the validation to fail.

- a token is only accepted for a few seconds (replay protection)

- the user password was never shared with the server

- the same username+password used on a different machine will generate a
  different shared secret, i.e. validation will fail.  In other words, even if
  the password is stolen, it doesn't work on any machine other than the one
  where the shared secret was originally generated.  It's "hardware locked."

                  --------------------------------

If you have multiple users on the sending machine, you need the usernames and
per-user-secrets to keep them separate.  If the sending machine is single user
(e.g. a raspberry pi just running one service), you can skip them, and the
hostname and machine-unique-data act as your username and password.

The shared secret is formed just by hashing together the username, user
password, hostname, and machine-unique-data.

The output token contains the username, source hostname, and time in
plaintext.  The username and/or hostname allow the receiving server to look up
its copy of the shared secret.  The hostname also allows for source-ip
validation, and time helps the receiving server to check for replay attempts.

The output token is a version tag, the plaintext mentioned above, and a hash
of the input string, the derived shared secret, the username, and the time.

The module will remember the last timestamp accepted from each {hostname,
username}, and require each subsequent request to be later than the previous
ones.  This implies a limit of 1 request per second.  You can turn this
behavior off in the validation request, or it will be disabled implicitly if
the module doesn't persist between calls.  In that case, the validator just
checks that the time of the request (included in the request) is within an
acceptance window of the server's current time.  This prevents replay attacks
only after the window has expired, so pick your window accordingly (along with
how closely you can keep your clocks in sync).

'''

import argparse, hashlib, json, os, socket, subprocess, sys, time
PY_VER = sys.version_info[0]

# ---------- global constants and types

DEBUG = False

DEFAULT_SECRETS_DB_FILENAME = 'k_auth_db.json'
DEFAULT_LAST_SEEN_TIMES_DB_FILENAME = 'k_auth_times.json'

TOKEN_VERSION = 'v2'


class AuthNError(Exception):
  pass


# ---------- general purpose helpers

def compare_hostnames(host1, host2):
  if host1 == host2: return True

  # Translate hostnmes to IP addresses and then compare those.
  try:
    if not isdigit[host1[0]]: host1 = socket.gethostbyname(host1)
    if not isdigit[host2[0]]: host2 = socket.gethostbyname(host2)
  except Exception: return False
  return host1 == host2


def safe_read(filename):
  try:
    with open(filename) as f: return f.read().strip()
  except Exception:
    return None


# ---------- authN general helpers

'''Get a private piece of data unique to the local machine.

This method tries a number of methods.  It doesn't really matter which one
works, so long as the generated per-machine-data is consistent, reasonably
unique, and private.  "Private" data ideally shouldn't be stored on the local
hard-disk, because such data is often backed up and becomes difficult to track
and protect.  It also certainly shouldn't be transmitted with every network
packet (the way a MAC address is).

When running in a Docker container (or similar), there really may be no
suitable container-specific secret.  The cgroup id changes each container
launch, so it fails the "consistent" requirement.  For this reason, this
method checks the environment variable $PUID (platform unique id), and will
unquestioningly use the value there if provided.  Docker container clients
should arrange for this variable to be populated.

The method will throw an exception if it can't generate a value that seems to
meet all the requirements.
'''
def get_machine_private_data():
  puid = os.environ.get('PUID')
  if puid: return puid

  # This works well on general Linux, but usually requires being root.
  puid = safe_read('/sys/class/dmi/id/product_uuid')
  if puid: return puid

  # This generally works well on Raspberry PI's.
  cpuinfo = safe_read('/proc/cpuinfo')
  for line in cpuinfo.split('\n'):
    if 'Serial' in line:
      _, puid = line.split(': ', 1)
      return puid

  # And finally fall back on the uuid of the root risk (this isn't ideal
  # because it's not guaranteed to be unique against major upgrade changes
  # and is sometimes available on disk in the boot logs).
  blk_ids = subprocess.check_output(['lsblk', '-nro', 'UUID,MOUNTPOINT'])
  for line in blk_ids.split('\n'):
    if line.endswith(' /'):
      puid, _ = line.split(' ', 1)
      return puid

  raise AuthNError('unable to find suitable machine private data. consider setting $PUID.')


def hasher(plaintext, trunc_len=20):
  if PY_VER == 3: plaintext = plaintext.encode('utf-8')
  return hashlib.sha1(plaintext).hexdigest()[:trunc_len]


def key_name(hostname, username): return '%s:%s' % (hostname, username)


def now(): return int(time.time())


# ---------- client-side authN logic

def generate_shared_secret(use_hostname=None, username='', user_password=''):
  hostname = use_hostname or socket.gethostname()
  hash_subject = '%s:%s:%s:%s' % (hostname, get_machine_private_data(), username, user_password)
  if DEBUG: print('DEBUG: shared secret hash subject: %s' % hash_subject)
  return '%s:%s:%s:%s' % (TOKEN_VERSION, hostname, username, hasher(hash_subject))


def generate_token(command, use_hostname=None, username='', user_password='', override_time=None):
  return generate_token_from_secret(
    command, generate_shared_secret(use_hostname, username, user_password),
    use_hostname, username, override_time)


def generate_token_from_secret(command, shared_secret,
                               use_hostname=None, username='', override_time=None):
  hostname = use_hostname or socket.gethostname()
  time_now = override_time or now()
  plaintext_context = '%s:%s:%s:%s' % (TOKEN_VERSION, hostname, username, time_now)
  hash_subject = '%s:%s:%s' % (plaintext_context, command, shared_secret)
  if DEBUG: print('DEBUG: hash subject: "%s"' % hash_subject)
  return '%s:%s' % (plaintext_context, hasher(hash_subject))


# ---------- server-side authN logic

LAST_RECEIVED_TIMES = {}


# Assumes shared secrets have already been loaded via load_secrets_db() or
# register_shared_secret(), and uses default db and validation params.
#
# returns:   okay?(bool), status(text), hostname, username, sent_time
def validate_token(token, command, hostname, username='', max_time_delta=30):
  shared_secret = get_shared_secret(hostname, username)
  if not shared_secret:
    return False, 'could not find registered shared secret for %s:%s' % (hostname, username), None, None, None
  return validate_token_from_secret(token, command, shared_secret, hostname, True, max_time_delta)


# returns:   okay?(bool), status(text), hostname, username, sent_time
def validate_token_from_secret(token, command, shared_secret,
                               expect_hostname=None,
                               must_be_later_than_last_request=True,
                               max_time_delta=30):
  try:
    token_version, hostname, username, sent_time_str, sent_auth = token.split(':', 4)
    sent_time = int(sent_time_str)
  except Exception:
    return False, 'token fails to parse', None, None, None

  if token_version != TOKEN_VERSION:
    return False, 'Wrong token/protocol version.   Saw "%s", expected "%s".' % (token_version, TOKEN_VERSION), hostname, username, sent_time

  if expect_hostname and not compare_hostnames(hostname, expect_hostname):
    return False, 'Wrong hostname.  Saw "%s", expected "%s".' % (hostname, expect_hostname), hostname, username, sent_time

  if max_time_delta:
    time_delta = abs(now() - sent_time)
    if time_delta > max_time_delta:
      return False, 'Time difference too high.  %d > %d.' % (time_delta, max_time_delta), hostname, username, sent_time

  if must_be_later_than_last_request:
    keyname = key_name(hostname, username)
    if keyname not in LAST_RECEIVED_TIMES:
      LAST_RECEIVED_TIMES[keyname] = sent_time
    else:
      if sent_time <= LAST_RECEIVED_TIMES[keyname]:
        return False, 'Received token is not later than a previous token: %d < %d' % (sent_time, LAST_RECEIVED_TIMES[keyname]), hostname, username, sent_time

  expect_token = generate_token_from_secret(command, shared_secret, hostname, username, sent_time)
  if token != expect_token: return False, 'Token fails to validate  Saw "%s", expected "%s".' % (token, expect_token), hostname, username, sent_time

  return True, 'ok', hostname, username, sent_time


# ---------- server-side persistence (shared secrets)

SECRETS_DB = None     # maps keyname -> shared secret

def load_secrets_db(db_filename=DEFAULT_SECRETS_DB_FILENAME):
  global SECRETS_DB
  try:
    with open(db_filename) as f: SECRETS_DB = json.loads(f.read())
    return True
  except Exception:
    SECRETS_DB = {}
    return False


# Must have already called load_secrets_db or register_shared_secret.
def get_shared_secret(hostname, username, db_filename=DEFAULT_SECRETS_DB_FILENAME):
  global SECRETS_DB
  if not SECRETS_DB and db_filename: load_secrets_db(db_filename)    
  return SECRETS_DB.get(key_name(hostname, username))


def register_shared_secret(shared_secret, db_filename=DEFAULT_SECRETS_DB_FILENAME):
  token_version, hostname, username, sec_hash = shared_secret.split(':')
  if token_version != TOKEN_VERSION: return False
  
  global SECRETS_DB
  if SECRETS_DB is None:
    if db_filename: load_secrets_db(db_filename)
    else: SECRETS_DB = {}

  keyname = key_name(hostname, username)
  SECRETS_DB[keyname] = shared_secret

  if db_filename:
    with open(db_filename, 'w') as f: f.write(json.dumps(SECRETS_DB))

  return True

# ---------- server-side persistence (last accept token times)

def load_last_seen_times(db_filename=DEFAULT_LAST_SEEN_TIMES_DB_FILENAME):
  global LAST_RECEIVED_TIMES
  try:
    with open(db_filename) as f: LAST_RECEIVED_TIMES = json.loads(f.read())
    return True
  except Exception:
    return False


def save_last_seen_times(db_filename=DEFAULT_LAST_SEEN_TIMES_DB_FILENAME):
  global LAST_RECEIVED_TIMES
  try:
    with open(db_filename, 'w') as f: f.write(json.dumps(LAST_RECEIVED_TIMES))
    return True
  except Exception:
    return False


# ---------- command-line interface

def main():
  ap = argparse.ArgumentParser(description='authN token generator')
  ap.add_argument('--username', '-u', default='', help='when using multiple-users per machine, this specifies which username to generate a secret for.  These do not need to match Linux usernames, they are arbitrary strings.')
  ap.add_argument('--password', '-p', default='', help='when using multiple-users per machine, this secret identifies a particular user')
  ap.add_argument('--hostname', '-H', default=None, help='hostname to generate/save secret for. (required for server-side commands;  autodetected if not specified for client-side commands)')
  
  group1 = ap.add_argument_group('client-side registration', 'shared secret generation')
  group1.add_argument('--generate', '-g', action='store_true', help='generate a shared secret that includes a machine-specific secret from this machine (i.e. must be run on the machine where future client requests will originate)')
  
  group2 = ap.add_argument_group('server-side registration', 'register a secret')
  group2.add_argument('--register', '-r', default=None, metavar='SECRET', help='register the specified shared secret (which must be generated on the client machine)')
  group2.add_argument('--filename', '-f', default=DEFAULT_SECRETS_DB_FILENAME, help='name of file in which to save registrations')

  group3 = ap.add_argument_group('token', 'creating or verifying tokens for a command')
  group3.add_argument('--command', '-c', default=None, help='specify the command to generate or verify a token for')
  group3.add_argument('--verify', '-v', default=None, metavar='TOKEN', help='verify the provided token for the specified command')
  group3.add_argument('--max-time-delta', '-m', default=60, type=int, help='max # seconds between token generation and consumption.')
  
  args = ap.parse_args()

  if args.generate:
    if not args.username: sys.exit('WARNING: username/password not specified.  Registering a host without usernames and passwords will allow anyone with access to the host to authenticate as the host.  If this is really what you want, specify "-" as the username.')
    username = '' if args.username == '-' else args.username
    if username and not args.password: sys.exit('really ought to have a password if username is specified.  Specify "-" if you really want to skip it.')
    password = '' if args.password == '-' else args.password
    print(generate_shared_secret(args.hostname, username, password))
    return 0

  elif args.register:
    ok = register_shared_secret(args.register, args.filename)
    if ok:
      print('Done.  Secrets file now has %d entries.' % len(SECRETS_DB))
      return 0
    print('Something went wrong (probably could not parse shared secret)')
    return -1

  elif args.command and not args.verify:
    print(generate_token(args.command, args.hostname, args.username, args.password))
    return 0

  elif args.verify:
    if not args.hostname: sys.exit('must provide --hostname, no way to guess what client hostname this was generated on')
    ok, status, hostname, username, sent = validate_token(args.verify, args.command, args.hostname, args.username, args.max_time_delta)
    print('validated? %s\nstatus: %s\ngenerated on host: %s\ngenerated by user: %s\ntime sent: %s (%s)' % (
      ok, status, hostname, username, sent, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sent))))
    return 0
    
  else:
    print('nothing to do...  specify one of --generate, --register, --command, --verify')
    return -2
  

if __name__ == '__main__':
  sys.exit(main())

