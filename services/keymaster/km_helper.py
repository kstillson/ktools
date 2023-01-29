#!/usr/bin/python3
'''km_helper: add or remove keys from an encrypted keymanager secrets file.

Truthfull, I don't use this anymore.  As you can probably tell from my other
files, I'm fussy about how data is aligned, and this tool isn't clever enough
to follow my convensions.  So what I do is use ../../pylib/tools/pcrypt.py to
manually decrypt km.data.pcrypt, and modify the plaintext directly.  It has a
very simple and human-friendly format, and will happily tolerate the addition
of white-space to make things align in a pleasant way.  Then run pcrypt again
to return the secrets file to a safe encrypted state (and don't forget to 
delete the temporary plaintext version!).

But if you're the sort who likes to have a CLI for everything, or if there's
some reason you need to automate the maintenance of your secrets data, this
script might come in handy.

Hopefully the arguments are reasonably straight forward: you tell the script
the --datafile you want to modify (generally km.data.pcrypt), provied the
--password it's encrypted with, the --keyname you want to add, the --secret
hidden behind that key's name, the --acl that limites who can access it, and
optionally a --comment to associate with the entry.

'''

import argparse, os, shutil, sys

# kcore stuff
import kcore.auth as A
import kcore.common2 as C
import kcore.uncommon as UC
import ktools.kmc as KMC

from km import Secret, Secrets


# ---------- helpers

def require(args, argname):
    val = getattr(args, argname)
    if not val: sys.exit(f'arg {argname} is required.')
    return val


def backup_db(db_filename):
    if not db_filename: return
    backup_filename = f'{db_filename}.prev'
    shutil.copyfile(db_filename, backup_filename)


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

  password = C.resolve_special_arg(args, 'password', required=False)
  secrets = Secrets(filename=args.datafile, rhs_type=Secret, password=password)

  # ----- alternate run modes

  if args.restart_km:
      ok = restart_server(args.restart_km, passwd)
      return 0 if status.ok else 1

  if args.testkey:
      with secrets.get_rw():
          secrets['testkey'] = Secret(secret='mysecret', acl=['*@*'], comment='test key')
      return 0

  # ----- remaining modes require decrypted database contents.

  keyname = require(args, 'keyname')

  if len(secrets) == 0: print(f'WARNING- No keys loaded from {secrets.filename}; starting fresh.')

  if args.remove:
      if keyname not in secrets: sys.exit(f'key to remove ({keyname}) not found in database')
      with secrets.get_rw():
          secrets.pop(keyname)
          print(f'ok: {secrets.filename} now has {len(secrets.cache)} entries.')
          return 0

  # ----- standard run mode: add a secret

  if keyname in secrets and not args.force: sys.exit(f'key {keyname} already exists in database, and --force not specified')

  new_secret = C.resolve_special_arg(args, 'secret')

  acl = list(map(str.split, args.acl.split(',')))
  entry = Secret(secret=new_secret, acl=acl, comment=args.comment)
  with secrets.get_rw():
      secrets[keyname] = entry
  print(f'ok: {secrets.filename} now has {len(secrets.cache)} entries.')
  return 0


if __name__ == '__main__':
    sys.exit(main())
