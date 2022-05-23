#!/usr/bin/python3
'''km_helper: add or remove keys from an encrypted keymanager secrets file.

TODO

'''

import argparse, getpass, json, os, sys

# kcore stuff
import kcore.auth as A
import kcore.common as C
import kcore.uncommon as UC
import ktools.kmc as KMC

from km import Secret, Secrets


# ---------- helpers

def get_special_arg(args, argname, required=True):
    '''Resolve - and $ special arg values. Also write resolved value back so we dont have to do it again.'''
    arg_val = getattr(args, argname)
    value = None
    if arg_val == "-":
        value = getpass.getpass(f'Enter value for {argname}: ')
        if value: setattr(args, argname, value)
    elif arg_val and arg_val.startswith('$'):
        varname = arg_val[1:]
        value = os.environ.get(varname)
        if not value: sys.exit(f'{argname} indicated to use environment variable {arg_val}, but variable is not set.')
        args.argname = value
    else: value = arg_val

    if required and not value: sys.exit(f'Unable to get required value for {argname}.')
    return value


def require(args, argname):
    val = getattr(args, argname)
    if not val: sys.exit(f'arg {argname} is required.')
    return val


def get_db_plaintext(db_filename, password):
    if not os.path.isfile(db_filename): return ''
    crypted = C.read_file(db_filename)
    if not crypted: sys.exit(f'unable to read encrypted db file {db_filename}')
    plaintext = UC.gpg_symmetric(crypted, password)
    if not plaintext or plaintext.startswith('ERROR'): sys.exit(f'decryption of {db_filename} failed.')
    return plaintext


def extract_keyname_from_blob(blob):
    _, sec_str = blob.split(' = ')
    sec = eval(sec_str)
    return sec.keyname


def is_keyname_in_plaintext(plaintext, keyname):
    for line in plaintext.split('\n'):
        if f"keyname='{keyname}'" in line: return True
    return False


def save_db(secrets, password, db_filename):
    plaintext = secrets.to_string()
    encrypted = UC.gpg_symmetric(plaintext, password, decrypt=False)
    if not 'PGP MESSAGE' in encrypted: sys.exit('encryption failed: ' + encrypted)
    backup_filename = f'{db_filename}.prev'
    if os.path.isfile(backup_filename): os.unlink(backup_filename)
    if os.path.isfile(db_filename): os.rename(db_filename, backup_filename)
    if db_filename == '-':
        print(encrypted)
    else:
        with open(db_filename, 'w') as f: f.write(encrypted)
    return len(secrets)


# ---------- attempt KM restart

def restart_server(hostport, password):
    resp = C.web_get(f'https://{hostport}/load',
                     post_dict={'password': password},
                     verify_ssl=False)
    if not resp.ok:
        print(f'error asking server to reload: [{resp.status_code}] {resp.exception} : {resp.text}')
        return False

    print(f'server reload ok: [{resp.status_code}] : {resp.text}')
    return True


# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description=__doc__)

  group2 = ap.add_argument_group('args to add a new secret')
  group2.add_argument('--comment',  '-c', default=None, help='comment to associate with key being added (this gets encrypted)')
  group2.add_argument('--keyname',  '-k', help='name of the key we are adding/changing')
  group2.add_argument('--hostname', '-H', help='hostname of the client machine that will be retrieving this key.')
  group2.add_argument('--password', '-p', default="-", help='password to decrypt --datafile.  Default ("-") to query from stdin.  Use "$X" to read password from environment variable X')
  group2.add_argument('--prefix',   '-P', default='%h-', help='prefix for the full key name. Defaults to "%%h-", which prefixes the hostname, and is usually what you want.')
  group2.add_argument('--secret',   '-s', default="-", help='contents of the key we are adding.  Default ("-") to query from stdin.  Use $X to read secret from environment varaible X.')

  group3 = ap.add_argument_group('alternate run modes')
  group3.add_argument('--remove',     '-Z', action='store_true', help='remove secret from --datafile with "keyname".  "hostname" and "secret" params not used.')
  group3.add_argument('--restart-km', '-R', default=None, help="Pass hostname:port of a keymanager server to attempt to restart to pick up added keys.  Note that if the server's data is in a docker filesystem, this probably won't have any effect and you need to rebuild the image instead.")
  group3.add_argument('--testkey',    '-T', action='store_true', help="Generate the contents of km-test.data.gpg; all other flags ignored.")

  # optional params
  ap.add_argument('--datafile',      '-d', default='km.data.gpg', help='name of encrypted secrets file we are going to modify')
  ap.add_argument('--force',         '-f', action='store_true', help='overwrite an existing secret with the new value')
  ap.add_argument('--override-host', '-O', default=None, help='save a tag that tells the server to expect this hostname/address, rather than the one from the client (i.e. --hostname).  Used to resolve DNS/NAT problems where the server sees a different address than the one the client knows.')
  ap.add_argument('--username',      '-u', default='', help='optional username that client must present to obtain keys')

  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])
  secrets = Secrets()

  # ----- alternate run modes

  if args.restart_km:
      ok = restart_server(args.restart_km, passwd)
      return 0 if status.ok else 1

  if args.testkey:
      secrets['*-testkey'] = Secret(secret='mysecret', comment='test key', override_expected_client_addr='*')
      save_db(secrets, 'test123', '-')
      return 0

  # ----- remaining modes require decrypted database contents.

  keyname = require(args, 'keyname')
  full_keyname = args.prefix.replace('%h', args.hostname) + keyname
  db_filename = require(args, 'datafile')
  password = get_special_arg(args, 'password')

  err = secrets.load_from_gpg_file(db_filename, password)
  if err: sys.exit(f'Unable to load secrets file: {err}')
  if len(secrets) == 0: print(f'WARNING- No keys loaded from {db_filename}; starting fresh.')

  if args.remove:
      if full_keyname not in secrets: sys.exit(f'key to remove ({full_keyname}) not found in database')
      secrets.pop(full_keyname)
      cnt = save_db(secrets, password, db_filename)
      print(f'ok: {db_filename} now has {cnt} entries.')
      return 0

  # ----- standard run mode: add a secret

  if full_keyname in secrets and not args.force: sys.exit(f'key {full_keyname} already exists in database, and --force not specified')

  hostname = require(args, 'hostname')
  new_secret = get_special_arg(args, 'secret')

  entry = Secret(secret=new_secret, username=args.username, comment=args.comment,
                 override_expected_client_addr=args.override_host)
  secrets[full_keyname] = entry
  cnt = save_db(secrets, password, db_filename)
  print(f'ok: {db_filename} now has {cnt} entries.')
  return 0


if __name__ == '__main__':
    sys.exit(main())
