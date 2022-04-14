#!/usr/bin/python3
'''A client-machine-locked authentication token generator.

An example session using the command-line interface:

>> [1 time] On the client machine, we generate a shared secret:
CLIENT$ k_auth -g -u user1 -p pass1
v2:blue2:user1:0d4b17b4080cc2ada031ceb276b5beec9f06b95e

>> [1 time] On the server, we register that secret:
SERVER$ k_auth -r v2:blue2:user1:0d4b17b4080cc2ada031ceb276b5beec9f06b95e

>> On the client, we generate a token to authenticate a command:
CLIENT$ k_auth -c 'command1' -u user1 -p pass1
v2:blue2:user1:1648266958:8c0c0da11eed666e3fefd0a30263f84ee6f671e7

>> On the server, we validate the token for that command:
SERVER$ k_auth -v v2:blue2:user1:1648266958:8c0c0da11eed666e3fefd0a30263f84ee6f671e7 -c 'command1'
validated? True

This successful validation demonstrates that:

- The command was not changed between token creation and validation.

- The token was created recently and hasn't been used before (i.e. replay
  protection).

- The same password was used during secret generation and token creation.

- The same machine was used for secret generation and token creation.
  i.e. even if the password is stolen, it won't work for token generation on
  any machine except the one where the secret was generated.

Note that we didn't have to store the generated secret on the client,
and the password was never given to the server.

                  --------------------------------

The shared secret is generated by combining client-machine-unique-data with
the username and password.  Why not just generate a random number?  Because
then we'd have to save it on the client.  The goal is to authenticate as the
user (using the password) *and* as the sending machine, but in a way the
client machine can be backed up without allowing someone possessing the backup
to impersonate the client machine.

If the sending machine is a single user system (e.g. a Raspberry Pi just
running a single service), you can skip the username and password: the
hostname and machine-unique-data take their place.  However, if the client is
not running as root and not on a Raspberry Pi, you might consider using a
password anyway, as the client-machine-unique-data might need to fall back to
using the root disk's UUID, which is often revealed in system logs.

Notes:

- "username" is unrelated to Linux uids; it's just an arbitrary string used to
  distinguish different authentication subjects from the same client machine.

- Tokens contain the username, source hostname, and time in plaintext.
  Including the hostname allows for source-ip validation.  You can set the
  hostname to "*" to disable source-ip validation, but tokens will still only
  validate if generated using the same client-generated secret (which is
  client-machnine specific, unless you override it by setting $PUID).

- The server-side logic will remember the last timestamp accepted from each
  {hostname+username}, and require each subsequent request to be later than
  the previous ones.  THIS IMPLIES A LIMIT OF 1 VALIDATION REQUEST PER SECOND.
  You can turn this check off in the validation request call, or it will be
  disabled implicitly if the module doesn't persist between checks.

- Indepentently, the server-side validator checks that the time of the token
  generation (included in the token) is within an acceptance window of the
  server's current time.  This prevents replay attacks only after the window
  has expired, so pick your acceptance window-size accordingly (along with how
  closely you can keep your client and server clocks in sync).

- If you want to register all your secrets on the server-side, rather than 
  switching back and forth between client and server (as outlined above), see
  services/keymaster/km-helper.py.
'''

import argparse, hashlib, json, os, socket, subprocess, sys, time
PY_VER = sys.version_info[0]

# ---------- global constants and types

DEBUG = False   # WARNING- outputs lots of secrets!
DEFAULT_MAX_TIME_DELTA = 30
DEFAULT_DB_FILENAME = 'k_auth_db.json'
TOKEN_VERSION = 'v2'

class AuthNError(Exception):
  pass


# ---------- general purpose helpers

def compare_hostnames(host1, host2):
  '''Compare hosts by name and/or IP address.'''
  
  if host1 == host2: return True

  # Translate hostnmes to IP addresses and then compare those.
  try:
    if not host1[0].isdigit(): host1 = socket.gethostbyname(host1)
    if not host2[0].isdigit(): host2 = socket.gethostbyname(host2)
  except Exception: return False
  return host1 == host2


def safe_read(filename):
  '''Return file contents or none on error'''
  try:
    with open(filename) as f: return f.read().strip()
  except Exception:
    return None


# ---------- authN general helpers

def get_machine_private_data():
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
  returned by this method from outside the container, or with a
  random-but-persistent per-container value.

  The method will throw an AuthNError exception if it can't generate a value
  that seems to meet all the requirements.
  '''
  puid = os.environ.get('PUID')
  if puid: return puid

  # This works well on general Linux, but by default requires root.  We don't
  # want to just attempt to read it and use it if it works, because then we
  # get different PUID values when root and non-root ask, and sometimes both
  # root and non-root users will want to generate tokens from the same
  # machine.  So...  It turns out root can grant read permissions to this file
  # to others, but it's non-persistent (i.e. reset upon reboot).  So we'll
  # check that the file perms allow "other+read", and only use this file if
  # so.  Therefore, to enable this (preferred) method, the sysadmin should add
  # this command to the system start-up process:
  #        chmod 444 /sys/class/dmi/id/product_uuid
  #
  fil = '/sys/class/dmi/id/product_uuid'
  if os.path.isfile(fil) and os.stat(fil).st_mode & 0o4 > 0:
    puid = safe_read(fil)
    if puid: return 'v2p:dpu:' + puid

  # This generally works well on Raspberry PI's.
  cpuinfo = safe_read('/proc/cpuinfo')
  for line in cpuinfo.split('\n'):
    if 'Serial' in line:
      _, puid = line.split(': ', 1)
      return 'v2p:csn:' + puid

  # And finally fall back on the uuid of the root risk (this isn't ideal
  # because it's not guaranteed to be unique against major upgrade changes
  # and is sometimes available on disk in the boot logs).
  blk_ids = subprocess.check_output(['lsblk', '-nro', 'UUID,MOUNTPOINT'])
  if PY_VER == 3: blk_ids = blk_ids.decode(sys.stdout.encoding)
  for line in blk_ids.split('\n'):
    if line.endswith(' /'):
      puid, _ = line.split(' ', 1)
      return 'v2p:rbi:' + puid

  raise AuthNError('unable to find suitable machine private data. consider setting $PUID.')


def hasher(plaintext):
  '''Return sha1 hash of a string as a string. Py2 or 3.'''
  if PY_VER == 3: plaintext = plaintext.encode('utf-8')
  return hashlib.sha1(plaintext).hexdigest()


def key_name(hostname, username): return '%s:%s' % (hostname, username)


def now(): return int(time.time())


# ---------- client-side authN logic

def generate_shared_secret(use_hostname=None, username='', user_password=''):
  '''Generate the shared secret used to register a client.

     Should be run on the client machine because machine-specific data is
     merged into the generated data (unless $PUID is set).

     The output of this method is a string that should be passed to register()
     on the server(s) where token validation will be performed.  The client
     does not need to save this shared secret; it will be automatically
     re-generated when generate_token() is called.

     You generally don't want to override the hostname: pass None and allow
     the method to autodetect the client's hostname.  This is because by
     default the server will check to see if a client's request is actually
     coming from the hostname it was registered with.  

     There are two advanced-usage exceptions: 

     (1) passing '*' as the hostname will tell the server not to check the
     remote address of a request based off this shared secret.  This can allow
     the secret to be retrieved by multiple hosts- HOWEVER- the shared secret
     still contains machine-specific data.  So if you really want the secret
     to be retriable from any host, you'll also need to set $PUID both before
     generating the secret with this method also, with the same $PUID value,
     each time any client generates a token that will be validated with the
     registration generated here.

     (2) it is sometimes convenient to generate a registration secret on some
     system other than the client (e.g. the server).  To do this, you get the
     machine-specific data from the client machine (see
     get_machine_private_data()), and securely transfer that to the system
     where you want to generate the shared secret registration, and set $PUID
     with the client's machine-specific data when calling this method. '''
  
  hostname = use_hostname or socket.gethostname()
  data_to_hash = '%s:%s:%s:%s' % (hostname, get_machine_private_data(), username, user_password)
  if DEBUG: print('DEBUG: client registration hash data: %s' % data_to_hash, file=sys.stderr)
  return '%s:%s:%s:%s' % (TOKEN_VERSION, hostname, username, hasher(data_to_hash))


def generate_token(command, use_hostname=None, username='', user_password='', override_time=None):
  '''Generate a token that authenticates "command".

     The generated token can be validated using validate_token() [below].
     Before validation will work, the client generating a token must register
     a shared secret with the server.  i.e. call generate_shared_secret() on
     the client, and then register() on the server.

     If "use_hostname" was used during shared secret generation, e.g. "*" was
     used to enable multi-host retrieval, the same "use_hostname" value must
     be passed here, or the token won't validate.  That's because this method
     works by re-generating the registration secret, so you don't have to 
     store it on the client.'''
  
  regenerated_registration = generate_shared_secret(use_hostname, username, user_password)
  return generate_token_given_shared_secret(
    command, regenerated_registration, use_hostname, username, override_time)


def generate_token_given_shared_secret(
    command, shared_secret, use_hostname=None, username='', override_time=None):
  '''Generate a token for "command" given a pre-generated shared secret.

     This method is really for internal-use by the validation side of the
     logic, but...

     Part of the idea of the auth module is that client's shouldn't have to
     save their shared secret, as it can be regenerated during token
     creation.  However, if for some reason you have a shared secret and
     want to generate a token from it, this method can do it for you.'''
    
  hostname = use_hostname or socket.gethostname()
  time_now = override_time or now()
  plaintext_context = '%s:%s:%s:%s' % (TOKEN_VERSION, hostname, username, time_now)
  data_to_hash = '%s:%s:%s' % (plaintext_context, command, shared_secret)
  if DEBUG: print('DEBUG: hash data: "%s"' % data_to_hash, file=sys.stderr)
  return '%s:%s' % (plaintext_context, hasher(data_to_hash))


# ---------- server-side authN logic

# This data is not internally persisted beyond module lifetime.
LAST_RECEIVED_TIMES = {}  # maps key_name() -> epoch seconds of most recent success.


def validate_token(token, command, client_addr,
                   must_be_later_than_last_check=True, max_time_delta=DEFAULT_MAX_TIME_DELTA):
  '''Validate "token" for "command", using a previously register()'ed shared secret.

     Passing None as client_addr will disable the check that the incoming
     request is coming from the hostname set during registration.  However, 
     this undermines an important aspect of this module's security model.

     Returns: okay?(bool), status(text), registered_hostname, username, sent_time'''
  
  token_version, registered_hostname, username, sent_time_str, sent_auth = token.split(':', 4)
  shared_secret = get_shared_secret_from_db(registered_hostname, username)
  if not shared_secret:
    return False, 'could not find client registration for %s:%s' % (registered_hostname, username), None, None, None
  return validate_token_given_shared_secret(
    token=token, command=command, shared_secret=shared_secret, client_addr=client_addr,
    must_be_later_than_last_check=must_be_later_than_last_check, max_time_delta=max_time_delta)


def validate_token_given_shared_secret(
      token, command, shared_secret, client_addr,
      must_be_later_than_last_check=True, max_time_delta=DEFAULT_MAX_TIME_DELTA):
  '''Validate "token" for "command", using a provided shared secret.

     Normally you validate tokens using validate_token().  However, if you're
     using some other mechanism other than this module's built-in database to
     persist registration shared-secrets, you can perform token validation
     using this method.

     The expected hostname will be pulled out of the provided shared secret.
     An expected hostname other than "*" will require a match between
     "client_addr" and the expected hostname (although that match can work by
     either hostname or IP address).  If you pass None as client_addr, it will
     bypass this check, but that undermines an important aspect of this
     module's security model.

     Returns: okay?(bool), status(text), registered_hostname, username, sent_time'''

  if DEBUG: print(f'DEBUG: starting validation token={token} command={command} shared_secret={shared_secret} client_addr={client_addr}', file=sys.stderr)
  try:
    token_version, expected_hostname, username, sent_time_str, sent_auth = token.split(':', 4)
    sent_time = int(sent_time_str)
  except Exception:
    return False, 'token fails to parse', None, None, None

  if token_version != TOKEN_VERSION:
    return False, f'Wrong token/protocol version.   Saw "{token_version}", expected "{TOKEN_VERSION}".', expected_hostname, username, sent_time

  if client_addr and expected_hostname != '*' and not compare_hostnames(expected_hostname, client_addr):
    return False, f'Wrong hostname.  Saw "{client_addr}", expected "{expected_hostname}".', expected_hostname, username, sent_time

  if max_time_delta:
    time_delta = abs(now() - sent_time)
    if time_delta > max_time_delta:
      return False, f'Time difference too high.  {time_delta} > %{max_time_delta}', expected_hostname, username, sent_time

  if must_be_later_than_last_check:
    keyname = key_name(expected_hostname, username)
    if keyname not in LAST_RECEIVED_TIMES:
      LAST_RECEIVED_TIMES[keyname] = sent_time
    else:
      if sent_time <= LAST_RECEIVED_TIMES[keyname]:
        return False, f'Received token is not later than a previous token: {sent_time} < {LAST_RECEIVED_TIMES[keyname]}', expected_hostname, username, sent_time

  expect_token = generate_token_given_shared_secret(command, shared_secret, expected_hostname, username, sent_time)
  if DEBUG: print(f'DEBUG: expect_token={expect_token} expected_hostname={expected_hostname}', file=sys.stderr)
  if token != expect_token: return False, f'Token fails to validate  Saw "{token}", expected "{expect_token}".', expected_hostname, username, sent_time

  return True, 'ok', expected_hostname, username, sent_time


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


def get_shared_secret_from_db(hostname, username, db_filename=DEFAULT_DB_FILENAME):
  global REGISTRATION_DB
  if not REGISTRATION_DB and db_filename: load_registration_db(db_filename)
  return REGISTRATION_DB.get(key_name(hostname, username))


def register(shared_secret, db_filename=DEFAULT_DB_FILENAME):
  token_version, hostname, username, _hash = shared_secret.split(':')
  if token_version != TOKEN_VERSION: return False

  global REGISTRATION_DB
  if REGISTRATION_DB is None:
    if db_filename: load_registration_db(db_filename)
    else: REGISTRATION_DB = {}

  keyname = key_name(hostname, username)
  REGISTRATION_DB[keyname] = shared_secret

  if db_filename:
    with open(db_filename, 'w') as f: f.write(json.dumps(REGISTRATION_DB))

  return True


# ---------- command-line interface

def parse_args(argv):
  ap = argparse.ArgumentParser(description='authN token generator')
  ap.add_argument('--username', '-u', default='', help='when using multiple-users per machine, this specifies which username to generate a registration for.  These do not need to match Linux usernames, they are arbitrary strings.')
  ap.add_argument('--password', '-p', default='', help='when using multiple-users per machine, this secret identifies a particular user')
  ap.add_argument('--hostname', '-H', default=None, help='hostname to generate/save registration for. (required for server-side commands;  autodetected if not specified for client-side commands)')

  group1 = ap.add_argument_group('client-side registration', 'client registration')
  group1.add_argument('--generate', '-g', action='store_true', help='generate a shared secret that includes a hashed machine-specific secret from this machine (i.e. must be run on the machine where future client requests will originate)')

  group2 = ap.add_argument_group('server-side registration', 'register a client (enable token validation from that client)')
  group2.add_argument('--register', '-r', default=None, metavar='SHARED_SECRET', help='register the shared secret from --generate into a validation server')
  group2.add_argument('--filename', '-f', default=DEFAULT_DB_FILENAME, help='name of file in which to save registrations')

  group3 = ap.add_argument_group('token', 'creating or verifying tokens for a command')
  group3.add_argument('--command', '-c', default=None, help='specify the command to generate or verify a token for')
  group3.add_argument('--verify', '-v', default=None, metavar='TOKEN', help='verify the provided token for the specified command')
  group3.add_argument('--max-time-delta', '-m', default=DEFAULT_MAX_TIME_DELTA, type=int, help='max # seconds between token generation and consumption.')

  group4 = ap.add_argument_group('special' 'other alternate modes')
  group4.add_argument('--extract-machine-secret', '-e', action='store_true', help='output the machine-unique-private data and stop.  Use -e on a would-be client machine, and then you can use that data with -s to generate shared secrets or tokens on a machine other than the real client machine.')
  group4.add_argument('--use-machine-secret', '-s', default=None, help='use the provided secret rather than querying the current machine for its real secret.  Equivalent to setting $PUID to the secret value.')

  return ap.parse_args(argv)

# ----------

def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])
  
  if args.extract_machine_secret:
    print(get_machine_private_data())
    return 0

  if args.use_machine_secret: os.environ['PUID'] = args.use_machine_secret

  if args.generate:
    if not args.password: sys.exit('WARNING: password not specified.  Registering a host without a password will allow anyone with access to the host to authenticate as the host.  If this is really what you want, specify "-" as the password.')
    password = '' if args.password == '-' else args.password
    if args.username and not password: sys.exit('specifying a username without a password is not useful.')
    print(generate_shared_secret(args.hostname, args.username, password))
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
    ok, status, hostname, username, sent = validate_token(
      token=args.verify, command=args.command,
      client_addr=args.hostname, max_time_delta=args.max_time_delta)
    print('validated? %s\nstatus: %s\ngenerated on host: %s\ngenerated by user: %s\ntime sent: %s (%s)' % (
      ok, status, hostname, username, sent, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sent))))
    return 0

  else:
    print('nothing to do...  specify one of --generate, --register, --command, --verify')
    return -2


if __name__ == '__main__':
  sys.exit(main())

