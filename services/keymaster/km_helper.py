#!/usr/bin/python3
'''km_helper: add or remove keys from an encrypted keymanager secrets file.

TODO

'''

import argparse, os, sys

# kcore stuff
import kcore.auth as A
import kcore.common as C
import kcore.uncommon as UC
import ktools.kmc as KMC

from km import Secret, Secrets


# ---------- helpers

def require(args, argname):
    val = getattr(args, argname)
    if not val: sys.exit(f'arg {argname} is required.')
    return val


def save_db(secrets, password, db_filename):
    plaintext = secrets.to_string()
    encrypted = UC.encrypt(plaintext, password)
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
  group2.add_argument('--acl',  '-a', default='', help='CSV list of username@hostname pairs allowed access to the secret')
  group2.add_argument('--comment',  '-c', default=None, help='comment to associate with key being added (gets encrypted)')
  group2.add_argument('--keyname',  '-k', help='name of the key we are adding/changing')
  group2.add_argument('--password', '-p', default="-", help='password to decrypt --datafile.  Default ("-") to query from stdin.  Use "$X" to read password from environment variable X')
  group2.add_argument('--secret',   '-s', default="-", help='contents of the key we are adding.  Default ("-") to query from stdin.  Use $X to read secret from environment varaible X.')

  group3 = ap.add_argument_group('alternate run modes')
  group3.add_argument('--remove',     '-Z', action='store_true', help='remove secret from --datafile with "keyname".  Other flags ignored.')
  group3.add_argument('--restart-km', '-R', default=None, help="Pass hostname:port of a keymanager server to attempt to restart to pick up added keys.  Note that if the server's data is in a docker filesystem, this probably won't have any effect and you need to rebuild the image instead.")
  group3.add_argument('--testkey',    '-T', action='store_true', help="Generate the contents of km-test.data.pcrypt; all other flags ignored.")

  # optional params
  ap.add_argument('--datafile',      '-d', default='km.data.pcrypt', help='name of encrypted secrets file we are going to modify')
  ap.add_argument('--force',         '-f', action='store_true', help='overwrite an existing secret with the new value')

  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])
  secrets = Secrets()

  # ----- alternate run modes

  if args.restart_km:
      ok = restart_server(args.restart_km, passwd)
      return 0 if status.ok else 1

  if args.testkey:
      secrets['testkey'] = Secret(
          secret='mysecret', acl=['*@*'], comment='test key')
      save_db(secrets, 'test123', '-')
      return 0

  # ----- remaining modes require decrypted database contents.

  keyname = require(args, 'keyname')
  db_filename = require(args, 'datafile')
  password = UC.resolve_special_arg(args, 'password')

  err = secrets.load_from_encrypted_file(db_filename, password)
  if err: sys.exit(f'Unable to load secrets file: {err}')
  if len(secrets) == 0: print(f'WARNING- No keys loaded from {db_filename}; starting fresh.')

  if args.remove:
      if keyname not in secrets: sys.exit(f'key to remove ({keyname}) not found in database')
      secrets.pop(keyname)
      cnt = save_db(secrets, password, db_filename)
      print(f'ok: {db_filename} now has {cnt} entries.')
      return 0

  # ----- standard run mode: add a secret

  if keyname in secrets and not args.force: sys.exit(f'key {keyname} already exists in database, and --force not specified')

  new_secret = UC.resolve_special_arg(args, 'secret')

  acl = list(map(str.split, args.acl.split(',')))
  entry = Secret(secret=new_secret, acl=acl, comment=args.comment)
  secrets[keyname] = entry
  cnt = save_db(secrets, password, db_filename)
  print(f'ok: {db_filename} now has {cnt} entries.')
  return 0


if __name__ == '__main__':
    sys.exit(main())
