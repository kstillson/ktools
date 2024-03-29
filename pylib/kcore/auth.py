#!/usr/bin/python3
'''A client-machine-locked authentication token generator.

This is essentially a shared-secret based system for a client to authenticate
to a server, but it's got a few extra twists:

1. The shared secret (hereafter referred to as the "client registration") is
derived from several components, including one that is obtained from the
hardware of the client (e.g. the motherboard serial number).  So even if the
same username/password is used, verification will fail if its attempted from a
different client machine.

2. Neither the client-machine-specific data nor the derived registration code
is stored anywhere on the disk of client machines, so even an attacker with
access to a full disk backup of the client cannot impersonate it.

3. The secret client registrations are stored on the server, but a mechanism
is provided to keep them encrypted, so full disk backups of the server
also shouldn't compromise security.

4. Authentication tokens also contain the time-stamp when they were created-
to prevent replay attacks, and a hash of the command being verified- to
prevent transferring tokens from a valid command to an invalid one.

                  --------------------------------

An example session using the command-line interface:

>> [one time] On the client machine, we generate the shared secret:
CLIENT$ k_auth -g -u user1 -p pass1
v2:blue2:user1:0d4b17b4080cc2ada031ceb276b5beec9f06b95e

>> [one time] On the server, we register that secret:
SERVER$ k_auth --db-passwd db123 -r v2:blue2:user1:0d4b17b4080cc2ada031ceb276b5beec9f06b95e

>> On the client, we generate a token to authenticate a command string:
CLIENT$ k_auth -c 'command1' -u user1 -p pass1
v2:blue2:user1:1648266958:8c0c0da11eed666e3fefd0a30263f84ee6f671e7

>> On the server, we verify the token for that command:
SERVER$ k_auth --db-passwd db123 -v v2:blue2:user1:1648266958:8c0c0da11eed666e3fefd0a30263f84ee6f671e7 -c 'command1'
verified? True

This successful verification demonstrates that:

- The command was not changed between token creation and verification.

- The token was created recently and hasn't been used before.

- The same password was used during secret generation and token creation.

- The same machine was used for secret generation and token creation.

Note that we didn't have to store the generated secret on the client,
and the password was never given to the server.


TODO: separate out a auth_base that depends only on hashlib, so it can work
with Circuit Python. (https://docs.circuitpython.org/en/latest/docs/library/hashlib.html)

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
using the root disk's UUID, which can be revealed in system logs.

Notes:

- "username" is unrelated to Linux uids; it's just an arbitrary string used to
  distinguish different authentication subjects from the same client machine.

- Tokens contain the username, client hostname, and time in plaintext.
  Including the hostname allows for source-ip verification.

- The server-side logic will remember the last timestamp accepted from each
  {hostname+username}, and require each subsequent request to be later than
  the previous ones.  THIS IMPLIES A LIMIT OF 1 VERIFICATION REQUEST PER SECOND.
  You can turn this check off in the verification request call, or it will be
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

import argparse, copy, hashlib, getpass, json, os, socket, subprocess, sys, time
from dataclasses import dataclass

import kcore.persister as P

PY_VER = sys.version_info[0]


# ---------- global constants

DEBUG = False   # WARNING- outputs lots of secrets!
DEFAULT_MAX_TIME_DELTA = 90
DEFAULT_DB_FILENAME = 'kcore_auth_db.data.pcrypt'
TOKEN_VERSION = 'v2'


# ---------- types

@dataclass
class SharedSecret:
  version_tag: str
  hostname: str
  username: str
  secret: str
  server_override_hostname: str = None   # see below.

  def lookup_key(self):
    return f'{self.server_override_hostname or self.hostname}:{self.username}'

  @staticmethod
  def from_string(src_str):
    return eval(src_str, {}, {'SharedSecret': SharedSecret})

  @staticmethod
  def generate(username, user_password, client_override_hostname=None):
    hostname = client_override_hostname or socket.gethostname()
    data_to_hash = '%s:%s:%s:%s' % (hostname, get_machine_private_data(), username, user_password)
    item = SharedSecret(version_tag=TOKEN_VERSION, hostname=hostname, username=username,
                        secret=hasher(data_to_hash))
    debug_msg(f'generating SharedSecret from plaintext: {data_to_hash} -> {item}')
    return item


@dataclass
class VerificationParams:
  db_passwd: str
  db_filename: str = DEFAULT_DB_FILENAME
  max_time_delta: int = DEFAULT_MAX_TIME_DELTA
  must_be_later_than_last_check: bool = True


# Regarding server_override_hostname: populating this field on the client-side
# has no effect.  Popuating it on the server-side (-H during registration),
# can be used in two ways:
#
# 1) If the server sees the client's hostname/IP-address differently from the
#    way the client sees itself (e.g. due to DNS or NAT), this field can be
#    used to give the server an expected hostname or IP address that the
#    client's connection will appear to come from, for source-address
#    verification.
#
# 2) If the field is set to "*", then server-side source-address verification is
#    disabled when validating tokens.  THE CLIENT'S MACHINE-SPECIFIC SECRET IS
#    STILL BLENDED INTO THE HASHED_SECRET, so this doesn't actually allow the
#    secret to be retrieved by "any" client, unless $PUID is used to override
#    machine secrets on all would-be clients during registration and token
#    generation.
#
# Note that shared secret lookup is done by a combination of hostname+username.
# So if you want a client to operate in normal machine-secret mode and in a
# shared (i.e. $PUID overriden) mode, the two registrations must use different
# usernames, so as not to collide.


@dataclass
class VerificationResults:
  ok: bool
  status: str
  registered_hostname: str
  username: str
  sent_time: int


class AuthNError(Exception):
  pass


# ---------- global state

LAST_RECEIVED_TIMES = {}  # maps command-specific-key-name -> epoch seconds of most recent success.
# LAST_RECEIVED_TIMES is not persisted beyond module lifetime.

# key for the dict is generated by SharedSecret.lookup_key()
REGISTRATION_DB = P.DictOfDataclasses(filename=None, rhs_type=SharedSecret)


# ---------- general purpose helpers

def compare_hosts(host1, host2):
  '''Compare hosts by name and/or IP address.'''

  if host1 == host2: return True

  # Translate hostnmes to IP addresses and then compare those.
  try:
    if not host1[0].isdigit(): host1 = socket.gethostbyname(host1)
    if not host2[0].isdigit(): host2 = socket.gethostbyname(host2)
  except Exception: return False
  return host1 == host2


def debug_msg(msg):
  if DEBUG: print('DEBUG: ' + msg, file=sys.stderr)


def hasher(plaintext):
  '''Return sha1 hash of a string as a string. Py2 or 3.'''
  if PY_VER == 3: plaintext = plaintext.encode('utf-8')
  return hashlib.sha1(plaintext).hexdigest()


def now(): return int(time.time())


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
  method checks the environment variable $PUID ("platform unique id"), and
  will unquestioningly use the value there if provided.  Docker container
  clients should arrange for this variable to be populated, preferably with
  the value returned by this method from outside the container, or with a
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


# ---------- client-side authN logic

def generate_shared_secret(username='', user_password='', client_override_hostname=None):
  '''Generate the shared secret used to register a client.

     Should be run on the client machine because machine-specific data is
     merged into the generated data (unless $PUID is used).

     The output of this method is a string that should be passed to register()
     on the server(s) where token verification will be performed.  The client
     does not need to save this shared secret; it will be automatically
     re-generated when generate_token() is called.
  '''
  return SharedSecret.generate(username, user_password, client_override_hostname)


def generate_token(command, username='', user_password='',
                   override_hostname=None, override_time=None):
  '''Generate a token that authenticates "command".

     The generated token can be verifyd using verify_token() [below].
     Before verification will work, the client generating a token must register
     a shared secret with the server.  i.e. call generate_shared_secret() on
     the client, and then register() on the server.

     Overriding hostname and/or time is intended for testing.  Using it in
     practice should just generate non-verifyable tokens.
  '''
  regenerated_registration = generate_shared_secret(username, user_password, client_override_hostname=override_hostname)

  return generate_token_given_shared_secret(
    command=command, shared_secret=regenerated_registration,
    username=username, use_hostname=override_hostname, override_time=override_time)


def generate_token_given_shared_secret(
    command, shared_secret, use_hostname=None, username='', override_time=None):
  '''Generate a token for "command" given a pre-generated shared secret.
     This method is intended for internal-use by the verification logic.
  '''

  # shared_secret.server_override_hostname is a server-side only concept, if
  # generate_token_given_shared_secret() is called from the client side, it will
  # likely be blank or different, so we need to exclude it from the contents of
  # the token's plaintext on both sides in order to get a match.
  if shared_secret.server_override_hostname:
    temp = copy.copy(shared_secret)
    temp.server_override_hostname = None
    shared_secret_str = str(temp)
  else:
    shared_secret_str = str(shared_secret)

  hostname = use_hostname or socket.gethostname()
  time_now = override_time or now()
  plaintext_context = '%s:%s:%s:%s' % (TOKEN_VERSION, hostname, username, time_now)
  data_to_hash = '%s:%s:%s' % (plaintext_context, command, shared_secret_str)
  hashed = hasher(data_to_hash)
  debug_msg(f'hash data: {data_to_hash} -> {hashed}')
  return '%s:%s' % (plaintext_context, hashed)


# ---------- server-side authN logic

def verify_token_with_params(token, command, client_addr, verification_params):
  return verify_token(token=token, command=command, client_addr=client_addr,
                      db_passwd=verification_params.db_passwd,
                      must_be_later_than_last_check=verification_params.must_be_later_than_last_check,
                      max_time_delta= verification_params.max_time_delta,
                      db_filename=verification_params.db_filename)


def verify_token(token, command, client_addr, db_passwd,
                 must_be_later_than_last_check=True, max_time_delta=DEFAULT_MAX_TIME_DELTA,
                 db_filename=DEFAULT_DB_FILENAME):
  '''Verify "token" for "command", using a previously registered shared secret.

     client_addr can be an IP address in string format, a hostname, or None.
     Passing None as client_addr will disable the check that the incoming
     request is coming from the hostname set during registration.  However,
     this undermines an important aspect of this module's security model.

     Returns: VerificationResults
  '''
  if not token: return VerificationResults(False, f'no authN token provided', None, None, None)
  token_version, token_hostname, username, sent_time_str, sent_auth = token.split(':', 4)
  shared_secret = get_shared_secret_from_db(db_passwd, db_filename, token_hostname, client_addr, username)
  if not shared_secret:
    return VerificationResults(False, f'could not find client registration for {token_hostname}:{username}', None, None, None)

  return verify_token_given_shared_secret(
    token=token, command=command, shared_secret=shared_secret, client_addr=client_addr,
    must_be_later_than_last_check=must_be_later_than_last_check, max_time_delta=max_time_delta)


def verify_token_given_shared_secret(
    token, command, shared_secret, client_addr,
    must_be_later_than_last_check=True, max_time_delta=DEFAULT_MAX_TIME_DELTA):
  '''Verify "token" for "command", using a provided shared secret.
     Returns VerificationResults.
  '''
  if isinstance(shared_secret, str): shared_secret = SharedSecret.from_string(shared_secret)

  debug_msg(f'starting verification token={token} command={command} shared_secret={shared_secret} client_addr={client_addr}')
  try:
    token_version, token_hostname, username, sent_time_str, sent_auth = token.split(':', 4)
    sent_time = int(sent_time_str)
  except Exception:
    return VerificationResults(False, 'token fails to parse', None, None, None)

  if token_version != TOKEN_VERSION:
    return VerificationResults(False, f'Wrong token/protocol version.   Saw "{token_version}", expected "{TOKEN_VERSION}".', shared_secret.hostname, username, sent_time)

  expected_hostname = shared_secret.server_override_hostname or shared_secret.hostname
  if client_addr and expected_hostname != '*' and not compare_hosts(expected_hostname, client_addr):
    return VerificationResults(False, f'Wrong hostname.  Saw "{client_addr}", expected "{expected_hostname}".', expected_hostname, username, sent_time)

  if max_time_delta:
    time_now = now()
    time_delta = abs(time_now - sent_time)
    if time_delta > max_time_delta:
      return VerificationResults(False, f'Time difference too high.  sent:{sent_time} now:{time_now},  delta {time_delta} > {max_time_delta}', expected_hostname, username, sent_time)

  if must_be_later_than_last_check:
    keyname = f'{expected_hostname}:{username}:{command}'
    if keyname not in LAST_RECEIVED_TIMES:
      LAST_RECEIVED_TIMES[keyname] = sent_time
    else:
      if sent_time <= LAST_RECEIVED_TIMES[keyname]:
        return VerificationResults(False, f'Received token is not later than a previous token: {sent_time} < {LAST_RECEIVED_TIMES[keyname]}', expected_hostname, username, sent_time)

  expect_token = generate_token_given_shared_secret(
    command=command, shared_secret=shared_secret,
    use_hostname=shared_secret.hostname, username=username, override_time=sent_time)
  debug_msg(f'expect_token={expect_token} expected_hostname={expected_hostname}')
  if token != expect_token: return VerificationResults(False, f'Token fails to verify  Saw "{token}", expected "{expect_token}".', expected_hostname, username, sent_time)

  return VerificationResults(True, 'ok', expected_hostname, username, sent_time)


# ---------- server-side persistence


def get_shared_secret_from_db(db_passwd, db_filename, token_hostname, client_addr=None, username=''):
  REGISTRATION_DB.filename = db_filename
  REGISTRATION_DB.password = db_passwd
  reg = REGISTRATION_DB.get_data()
  if not reg:
    debug_msg(f'failed to load registration db: {REGISTRATION_DB.__dict__}')
    return None

  srch = f'{token_hostname}:{username}'
  lookup = reg.get(srch)
  if lookup:
    debug_msg(f'returning token hostname match: {token_hostname}')
    return lookup
  else: debug_msg(f'trying {srch} in reg db didnt work...')

  srch = f'{client_addr}:{username}'
  lookup = reg.get(srch)
  if lookup:
    debug_msg(f'returning client address hostname match: {client_addr}')
    return lookup
  else: debug_msg(f'trying {srch} in reg db didnt work...')

  srch = f'*:{username}'
  lookup = reg.get(srch)
  if lookup:
    debug_msg(f'returning wildcard hostname match')
    return lookup
  else: debug_msg(f'trying {srch} in reg db didnt work...')

  debug_msg(f'no matching entry in reg_db: {reg.__dict__}')


def register(shared_secret, db_passwd, db_filename=DEFAULT_DB_FILENAME,
             server_override_hostname=None):
  if isinstance(shared_secret, str): shared_secret = SharedSecret.from_string(shared_secret)
  if shared_secret.version_tag != TOKEN_VERSION: return False
  if server_override_hostname: shared_secret.server_override_hostname = server_override_hostname

  REGISTRATION_DB.filename = db_filename
  REGISTRATION_DB.password = db_passwd
  with REGISTRATION_DB.get_rw() as db:
    db[shared_secret.lookup_key()] = shared_secret

  return True


# ---------- command-line interface

def parse_args(argv):
  ap = argparse.ArgumentParser(description='authN token generator')
  ap.add_argument('--username', '-u', default='', help='Does not need to match Linux usernames, they are arbitrary strings.')
  ap.add_argument('--password', '-p', default='', help='when using multiple-users per machine, this secret identifies a particular user')

  group1 = ap.add_argument_group('client-side registration', 'client registration')
  group1.add_argument('--generate', '-g', action='store_true', help='generate a shared secret that includes a hashed machine-specific secret from this machine (i.e. must be run on the machine where future client requests will originate, unless $PUID is used.)')

  group2 = ap.add_argument_group('server-side registration', 'register a client (enable token verification from that client)')
  group2.add_argument('--register', '-r', default=None, metavar='SHARED_SECRET', help='register the shared secret from the client\'s --generate command')
  group2.add_argument('--override-hostname', '-O', default=None, help='use this as the expected hostname/IP when checking clients peer address.  "*" to disable the check.')
  group2.add_argument('--db-filename', '-f', default=DEFAULT_DB_FILENAME, help='name of file on server to store shared registration secrets')
  group2.add_argument('--db-passwd', '-P', default=None, help='encryption passphrase for --filename.  Default ("-") to query from stdin.  Use "$X" to read password from environment variable X')

  group3 = ap.add_argument_group('create token', 'creating an authentication token on the client')
  group3.add_argument('--command', '-c', default=None, help='specify the command to generate or verify a token for')

  group4 = ap.add_argument_group('verify token', 'check token on the server')
  group4.add_argument('--verify', '-v', default=None, metavar='TOKEN', help='verify the provided token.  Must also provide --hostname, --command, and --db-passwd.  Must provide --username and --password if used, and --filename if not using the default.')
  group4.add_argument('--hostname', '-H', default='', help='hostname the token being verified came from')
  group4.add_argument('--max-time-delta', '-m', default=DEFAULT_MAX_TIME_DELTA, type=int, help='max # seconds between token generation and consumption.')

  group5 = ap.add_argument_group('special' 'other alternate modes')
  group5.add_argument('--debug', '-d', action='store_true', help='activate debugging info.  WARNING- outputs lots of secrets!')
  group5.add_argument('--extract-machine-secret', '-e', action='store_true', help='run on the client to output the machine-unique-private data and stop.  See -s.')
  group5.add_argument('--use-machine-secret', '-s', default=None, help='on the client, use this provided client machine secret rather than querying the machine for its real secret.  Equivalent to setting $PUID.')

  return ap.parse_args(argv)

# ----------

def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  global DEBUG
  if args.debug: DEBUG = True

  if args.extract_machine_secret:
    print(get_machine_private_data())
    return 0

  if args.use_machine_secret: os.environ['PUID'] = args.use_machine_secret

  if args.db_passwd:
    if args.db_passwd == "-":
        args.db_passwd = getpass.getpass(f'Enter value for registration database: ')
    elif args.db_passwd.startswith('$'):
        varname = args.db_passwd[1:]
        tmp = os.environ.get(args.db_passwd[1:])
        if tmp: args.db_passwd = tmp
        else: sys.exit(f'--db-passwd indicated to use {args.db_passwd}, but variable is not set.')

  if args.generate:
    if not args.password: sys.exit('WARNING: password not specified.  Registering a host without a password will allow anyone with access to the host to authenticate as the host.  If this is really what you want, specify "-" as the password.')
    password = '' if args.password == '-' else args.password
    print(str(generate_shared_secret(args.username, password, args.hostname)))
    return 0

  elif args.register:
    if not args.db_passwd: sys.exit('must provide --db-passwd in order to --register.')
    shared_secret = SharedSecret.from_string(args.register)
    ok = register(shared_secret, args.db_passwd, args.db_filename,
                  server_override_hostname=args.override_hostname)
    if ok:
      print('Done.  Registration file now has %d entries.' % len(REGISTRATION_DB))
      return 0
    print('Something went wrong (wrong --db-passwd?)')
    return -1

  elif args.command and not args.verify:
    print(generate_token(args.command, args.username, args.password))
    return 0

  elif args.verify:
    if not args.db_passwd: sys.exit('must provide --db-passwd to --verify.')
    if not args.hostname: print('WARNING- no client address provided via --hostname flag, so client host checking is disabled.')
    rslt = verify_token(token=args.verify, command=args.command, client_addr=args.hostname,
                          db_passwd=args.db_passwd, max_time_delta=args.max_time_delta)
    friendly_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rslt.sent_time))
    print(f'verified? {rslt.ok}\nstatus: {rslt.status}\ngenerated on host: {rslt.registered_hostname}\ngenerated by user: {rslt.username}\ntime sent: {rslt.sent_time} ({friendly_time})')
    return 0

  else:
    print('nothing to do...  specify one of --generate, --register, --command, --verify')
    return -2


if __name__ == '__main__':
  sys.exit(main())
