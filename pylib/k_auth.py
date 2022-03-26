#!/usr/bin/python3
'''A client-machine-locked authentication token generator.

Inputs:
  - a string (e.g. a command to run on a server after authentication)
  - (optionally) a username
  - (optionally) a password

Implicid inputs:
  - a piece of private unique data extracted from the client machine's hardware
  - the current time

Output:
  - a string that ties all the above together into an authN token.

                  --------------------------------

An example session using the command-line interface:

>> On the client machine, we generate a machine+user+password registration:
   (note the hostname "blue2" is auto-detected)
./k_auth.py -g -u user1 -p pass1
v2:blue2:user1:0d4b17b4080cc2ada031ceb276b5beec9f06b95e

>> On the server, we register that host+user:
./k_auth.py -r v2:blue2:user1:0d4b17b4080cc2ada031ceb276b5beec9f06b95e
Done.  Registration file now has 1 entries.

>> Back on the client, we generate a token that authenticates a command:
./k_auth.py -c 'command1' -u user1 -p pass1
v2:blue2:user1:1648266958:8c0c0da11eed666e3fefd0a30263f84ee6f671e7

>> On the server, we validate the token for that command:
./k_auth.py -v v2:blue2:user1:1648266958:8c0c0da11eed666e3fefd0a30263f84ee6f671e7 -c 'command1'
validated? True

This successful validation demonstrates that:

- The command was not changed between token creation and validation.

- The token was created very recently and hasn't been used before
  (i.e. replay protection).

- The same password was used during registration and token creation
  (and note that password was never shared with the server).

- The client machine was used for registration generation and token creation.
  i.e. even if the password is stolen, it won't work for token generation on
  any machine except the one where the registration was generated in the first
  step.  It's "hardware locked."

                  --------------------------------

If you have multiple users on the sending machine, you need the usernames and
per-user-passwords to keep them separate.  If the sending machine is single
user (e.g. a raspberry pi just running one service), you can skip them, and
the hostname and machine-unique-data act as your username and password.

The generated registration is formed just by hashing together the username,
user password, hostname, and machine-unique-data.

The output token contains the username, source hostname, and time in
plaintext.  The username and/or hostname allow the receiving server to look up
its copy of the registration data.  The hostname also allows for source-ip
validation, and time helps the receiving server to check for replay attempts.

The output token is a version tag, the plaintext mentioned above, and a hash
of the input string, the derived registration data, the username, and the time.

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

DEFAULT_MAX_TIME_DELTA = 30
DEFAULT_DB_FILENAME = 'k_auth_db.json'

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

This function tries a number of methods of getting machine-private data.  It
doesn't really matter which one works, so long as the generated
per-machine-data is consistent, reasonably unique, and private.  "Private"
data ideally shouldn't be stored on the local hard-disk, because such data is
often backed up and becomes difficult to track and protect.  It also certainly
shouldn't be transmitted with every network packet (the way a MAC address is).

When running in a Docker container (or similar), there really may be no
suitable container-specific secret.  The cgroup id changes each container
launch, so it fails the "consistent" requirement.  For this reason, this
method checks the environment variable $PUID (platform unique id), and will
unquestioningly use the value there if provided.  Docker container clients
should arrange for this variable to be populated, preferably with the value
returned by this method from outside the container, or preferrably with a
random-but-persistent per-container value.

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
  if PY_VER == 3: blk_ids = blk_ids.decode(sys.stdout.encoding)
  for line in blk_ids.split('\n'):
    if line.endswith(' /'):
      puid, _ = line.split(' ', 1)
      return puid

  raise AuthNError('unable to find suitable machine private data. consider setting $PUID.')


def hasher(plaintext):
  if PY_VER == 3: plaintext = plaintext.encode('utf-8')
  return hashlib.sha1(plaintext).hexdigest()


def key_name(hostname, username): return '%s:%s' % (hostname, username)


def now(): return int(time.time())


# ---------- client-side authN logic

def generate_client_registration(use_hostname=None, username='', user_password=''):
  hostname = use_hostname or socket.gethostname()
  data_to_hash = '%s:%s:%s:%s' % (hostname, get_machine_private_data(), username, user_password)
  if DEBUG: print('DEBUG: client registration hash data: %s' % data_to_hash)
  return '%s:%s:%s:%s' % (TOKEN_VERSION, hostname, username, hasher(data_to_hash))


def generate_token(command, use_hostname=None, username='', user_password='', override_time=None):
  regenerated_registration = generate_client_registration(use_hostname, username, user_password)
  return generate_token_given_registration(
    command, regenerated_registration, use_hostname, username, override_time)


def generate_token_given_registration(
    command, registration_blob, use_hostname=None, username='', override_time=None):
  hostname = use_hostname or socket.gethostname()
  time_now = override_time or now()
  plaintext_context = '%s:%s:%s:%s' % (TOKEN_VERSION, hostname, username, time_now)
  data_to_hash = '%s:%s:%s' % (plaintext_context, command, registration_blob)
  if DEBUG: print('DEBUG: hash data: "%s"' % data_to_hash)
  return '%s:%s' % (plaintext_context, hasher(data_to_hash))


# ---------- server-side authN logic

# This data is not persisted beyond module lifetime by default.
# If you want to add persistenace, you can access it here.
LAST_RECEIVED_TIMES = {}  # maps key_name() -> epoch seconds of most recent success.


# returns:   okay?(bool), status(text), hostname, username, sent_time
def validate_token(token, command, max_time_delta=DEFAULT_MAX_TIME_DELTA):
  token_version, hostname, username, sent_time_str, sent_auth = token.split(':', 4)
  registration_blob = get_registration_blob(hostname, username)
  if not registration_blob:
    return False, 'could not find client registration for %s:%s' % (hostname, username), None, None, None
  return validate_token_given_registration(token, command, registration_blob, hostname, True, max_time_delta)


# returns:   okay?(bool), status(text), hostname, username, sent_time
def validate_token_given_registration(
      token, command, registration_blob, expect_hostname=None,
      must_be_later_than_last_check=True, max_time_delta=DEFAULT_MAX_TIME_DELTA):
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

  if must_be_later_than_last_check:
    keyname = key_name(hostname, username)
    if keyname not in LAST_RECEIVED_TIMES:
      LAST_RECEIVED_TIMES[keyname] = sent_time
    else:
      if sent_time <= LAST_RECEIVED_TIMES[keyname]:
        return False, 'Received token is not later than a previous token: %d < %d' % (sent_time, LAST_RECEIVED_TIMES[keyname]), hostname, username, sent_time

  expect_token = generate_token_given_registration(command, registration_blob, hostname, username, sent_time)
  if token != expect_token: return False, 'Token fails to validate  Saw "%s", expected "%s".' % (token, expect_token), hostname, username, sent_time

  return True, 'ok', hostname, username, sent_time


# ---------- server-side persistence

REGISTRATION_DB = None     # maps keyname -> registration blob

def load_registration_db(db_filename=DEFAULT_DB_FILENAME):
  global REGISTRATION_DB
  try:
    with open(db_filename) as f: REGISTRATION_DB = json.loads(f.read())
    return True
  except Exception:
    REGISTRATION_DB = {}
    return False


def get_registration_blob(hostname, username, db_filename=DEFAULT_DB_FILENAME):
  global REGISTRATION_DB
  if not REGISTRATION_DB and db_filename: load_registration_db(db_filename)
  return REGISTRATION_DB.get(key_name(hostname, username))


def register(registration_blob, db_filename=DEFAULT_DB_FILENAME):
  token_version, hostname, username, _hash = registration_blob.split(':')
  if token_version != TOKEN_VERSION: return False

  global REGISTRATION_DB
  if REGISTRATION_DB is None:
    if db_filename: load_registration_db(db_filename)
    else: REGISTRATION_DB = {}

  keyname = key_name(hostname, username)
  REGISTRATION_DB[keyname] = registration_blob

  if db_filename:
    with open(db_filename, 'w') as f: f.write(json.dumps(REGISTRATION_DB))

  return True


# ---------- command-line interface

def main(argv):
  ap = argparse.ArgumentParser(description='authN token generator')
  ap.add_argument('--username', '-u', default='', help='when using multiple-users per machine, this specifies which username to generate a registration for.  These do not need to match Linux usernames, they are arbitrary strings.')
  ap.add_argument('--password', '-p', default='', help='when using multiple-users per machine, this secret identifies a particular user')
  ap.add_argument('--hostname', '-H', default=None, help='hostname to generate/save registration for. (required for server-side commands;  autodetected if not specified for client-side commands)')

  group1 = ap.add_argument_group('client-side registration', 'client registration')
  group1.add_argument('--generate', '-g', action='store_true', help='generate a client registration that includes a hashed machine-specific secret from this machine (i.e. must be run on the machine where future client requests will originate)')

  group2 = ap.add_argument_group('server-side registration', 'register a client (enable token validation from that client)')
  group2.add_argument('--register', '-r', default=None, metavar='REGISTRATION_BLOB', help='register the output of --generate (which must be generated on the client machine)')
  group2.add_argument('--filename', '-f', default=DEFAULT_DB_FILENAME, help='name of file in which to save registrations')

  group3 = ap.add_argument_group('token', 'creating or verifying tokens for a command')
  group3.add_argument('--command', '-c', default=None, help='specify the command to generate or verify a token for')
  group3.add_argument('--verify', '-v', default=None, metavar='TOKEN', help='verify the provided token for the specified command')
  group3.add_argument('--max-time-delta', '-m', default=DEFAULT_MAX_TIME_DELTA, type=int, help='max # seconds between token generation and consumption.')

  group4 = ap.add_argument_group('special' 'other alternate modes')
  group4.add_argument('--extract-machine-secret', '-e', action='store_true', help='output the machine-unique-private data and stop.  Use -e on a would-be client machine, and then you can use that data with -s to generate shared secrets or tokens on a machine other than the real client machine.')
  group4.add_argument('--use-machine-secret', '-s', default=None, help='use the provided secret rather than querying the current machine for its real secret.  Equivalent to setting $PUID to the secret value.')

  args = ap.parse_args(argv)

  if args.extract_machine_secret:
    print(get_machine_private_data())
    return 0

  if args.use_machine_secret: os.environ['PUID'] = args.use_machine_secret

  if args.generate:
    if not args.password: sys.exit('WARNING: password not specified.  Registering a host without a password will allow anyone with access to the host to authenticate as the host.  If this is really what you want, specify "-" as the password.')
    password = '' if args.password == '-' else args.password
    if args.username and not password: sys.exit('specifying a username without a password is not useful.')
    print(generate_client_registration(args.hostname, args.username, password))
    return 0

  elif args.register:
    ok = register(args.register, args.filename)
    if ok:
      print('Done.  Registration file now has %d entries.' % len(REGISTRATION_DB))
      return 0
    print('Something went wrong (probably could not parse shared secret)')
    return -1

  elif args.command and not args.verify:
    print(generate_token(args.command, args.hostname, args.username, args.password))
    return 0

  elif args.verify:
    ok, status, hostname, username, sent = validate_token(args.verify, args.command, args.max_time_delta)
    print('validated? %s\nstatus: %s\ngenerated on host: %s\ngenerated by user: %s\ntime sent: %s (%s)' % (
      ok, status, hostname, username, sent, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sent))))
    return 0

  else:
    print('nothing to do...  specify one of --generate, --register, --command, --verify')
    return -2


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))

