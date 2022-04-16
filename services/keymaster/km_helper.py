#!/usr/bin/python3
'''km_helper: add or remove keys from an encrypted keymanager secrets file.

Adding keys requires a "platform unique identifier" ("PUID") from the machine
that will eventually retrieve the secret (i.e. the "client").  You'll need to
manually get that from the would-be client, and provide it to this script.  To
retrieve a PUID, install kgcore/pylib/tools and run: "kmc -E x".

You can provide the PUID via the flag --puid, or you can allow this script to
maintain a database of PUID's, so you won't need to provide a PUID beyond the
first time you add a key for a given client.  The --puid-db will be encrypted
using the same password as the primary secrets datafile.

'''

import argparse, getpass, json, os, sys

# kcore stuff
import kcore.auth as A
import kcore.common as C
import kcore.uncommon as UC
import ktools.kmc as KMC

from km import Secret, Secrets

# ---------- the PUID secrets database

class Puids(dict):
    def load_from_gpg_file(self, filename, password):
        try:
            with open(filename) as f: crypted = f.read()
            return self.update(json.loads((UC.gpg_symmetric(crypted, password))))
        except IOError:
            print(f'WARNING: {filename} does not exist; creating new one.')
        except json.decoder.JSONDecodeError:
            sys.exit(f'unable to decode puids database {filename}')
            
    def save_to_gpg_file(self, filename, password):
        with open(filename, 'w') as f:
            f.write(UC.gpg_symmetric(json.dumps(self), password, decrypt=False))

PUIDS = Puids()

# ---------- helpers

# TODO: impl ! prefix

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
    if not os.path.isfile(db_filename): return None
    crypted = C.read_file(db_filename)
    if not crypted: sys.exit(f'unable to read encrypted db file {db_filename}')
    plaintext = UC.gpg_symmetric(crypted, password)
    if not plaintext: sys.exit(f'decryption of {db_filename} failed.')
    return plaintext
   

def extract_keyname_from_blob(blob):
    _, sec_str = blob.split(' = ')
    sec = eval(sec_str)
    return sec.keyname


def is_keyname_in_plaintext(plaintext, keyname):
    for line in plaintext.split('\n'):
        if f"keyname='{keyname}'" in line: return True
    return False


def remove_keyname_from_plaintext(plaintext, keyname):
    out = ''
    for line in plaintext.split('\n'):
        if not f"keyname='{keyname}'" in line: out += line + '\n'
    return out


def save_db_from_plaintext(plaintext, password, db_filename):
    encrypted = UC.gpg_symmetric(plaintext, password, decrypt=False)
    if not 'PGP MESSAGE' in encrypted: sys.exit('encryption failed: ' + encrypted)
    backup_filename = f'{db_filename}.prev'
    if os.path.isfile(backup_filename): os.unlink(backup_filename)
    if os.path.isfile(db_filename): os.rename(db_filename, backup_filename)
    with open(db_filename, 'w') as f: f.write(encrypted)
    return True
    


# ---------- add new key

def add_key_from_blob(blob, password, db_filename, force=False):
    plaintext = get_db_plaintext(db_filename, password)
    if not plaintext:
        plaintext = ''
        print(f'WARNING- {db_filename} does not exist; creating a new one.')

    # check if this key is already regsitered
    keyname = extract_keyname_from_blob(blob)
    if is_keyname_in_plaintext(plaintext, keyname):
        if force:
            plaintext = remove_keyname_from_plaintext(plaintext, keyname)
        else:
            sys.exit(f'key with name {keyname} already exists and --force not specified.')
        
    # add the new blob...
    plaintext += f'\n{blob.strip()}\n'
    save_db_from_plaintext(plaintext, password, db_filename)
    return plaintext.count('Secret(')

    
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
  ap.add_argument('--comment', '-c', default=None, help='comment to associate with key being added (this gets encrypted)')
  ap.add_argument('--datafile', '-d', default='km.data.gpg', help='name of encrypted secrets file we are going to modify')
  ap.add_argument('--force', '-f', action='store_true', help='overwrite an existing secret with the new value')
  ap.add_argument('--password', '-p', default="-", help='password to decrypt both --datafile and --puid-db.  Default ("-") to query from stdin.  Use "$X" to read password from environment variable X, use !Y to query key-manager key Y to use as password (kinda meta, huh?)')
  ap.add_argument('--puid', default='', help='skip use of --puid-pdb and just use given string as the PUID')
  ap.add_argument('--puid-db', default='puid.data.gpg', help='name of encrypted database of machine secrets')
  ap.add_argument('--user_password', '-P', default='', help='optional password that client must present to obtain keys')
  ap.add_argument('--username', '-u', default='', help='optional username that client must present to obtain keys')

  group0 = ap.add_argument_group('args needed to add a new key')
  group0.add_argument('--keyname', '-k', help='name of the key we are changing')
  group0.add_argument('--hostname', '-H', help='hostname of the client machine that will be retrieving this key.  Also controls what entry will be sought in --puid-db')
  group0.add_argument('--secret', '-s', default="-", help='contents of the key we are adding.  Default ("-") to query from stdin.  Use $X to read secret from environment varaible X.')
  
  group1 = ap.add_argument_group('add a pre-generated registration blob')
  group1.add_argument('--blob', '-b', default=None, help='store a secret registration blob generated by "kmc -g".  hostname, keyname, and secret are ready from the blob (and thus flag values are ignored).  Provide the registration blob to as a value to this flag, or specify "-" to read the blob from stdin, or "$X" to read the blob from environment variable X.')

  group2 = ap.add_argument_group('alternate run modes')
  group2.add_argument('--register-puid', '-r', action='store_true', help='skip adding a new secret to --datafile and instead add a new PUID (provided by --puid) value to --puid-db.')
  group2.add_argument('--remove', '-Z', action='store_true', help='remove secret from --datafile with "keyname".  "hostname" and "secret" params not used.')
  group2.add_argument('--restart-km', '-R', default=None, help="Pass hostname:port of a keymanager server to attempt to restart to pick up added keys.  Note that if the server's data is in a docker filesystem, this probably won't have any effect and you need to rebuild the image instead.")
  group2.add_argument('--testkey', '-T', action='store_true', help="Generate the contents of km-test.data.gpg; all other flags ignored.")

  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  # ----- alternate run modes
  
  if args.blob:
      blob = get_special_arg(args, 'blob')
      passwd = get_special_arg(args, 'password')
      new_cnt = add_key_from_blob(blob, passwd, args.datafile, args.force)
      print(f'ok: {args.datafile} now has {new_cnt} entries.')
      return 0

  if args.register_puid:
      if not args.puid: args.puid = '-'  # assume they want us to read from stdin
      new_puid = get_special_arg(args, 'puid')
      filename = require(args, 'puid_db')
      passwd = get_special_arg(args, 'password')
      PUIDS.load_from_gpg_file(filename, passwd)
      PUIDS[require(args, 'hostname')] = new_puid
      PUIDS.save_to_gpg_file(filename, passwd)
      print(f'ok: {filename} now has {len(PUIDS)} entries.')
      return 0

  if args.remove:
      keyname = require(args, 'keyname')
      db_filename = require(args, 'datafile')
      password = get_special_arg(args, 'password')
      plaintext = get_db_plaintext(db_filename, password)
      old_count = plaintext.count('Secret(')
      new_plaintext = remove_keyname_from_plaintext(plaintext, keyname)
      new_count = new_plaintext.count('Secret(')
      if new_count != old_count - 1:
          sys.exit(f'something went wrong removing {keyname}; db unchanged.  old_count={old_count} new_count={new_count}')
      save_db_from_plaintext(new_plaintext, password, db_filename)
      print(f'ok: {db_filename} now has {new_count} entries.')
      return 0

  if args.restart_km:
      ok = restart_server(args.restart_km, passwd)
      return 0 if status.ok else 1
  
  if args.testkey:
      os.environ['PUID'] = 'test'
      plaintext = KMC.generate_key_registration(keyname='testkey', key='mysecret', override_hostname='*', comment='zero value test key') + '\n'
      crypted = UC.gpg_symmetric(plaintext, password='test123', decrypt=False)
      print(crypted)
      return 0            

  # ----- standard run mode: adding a key

  hostname = require(args, 'hostname')
  keyname = require(args, 'keyname')
  secret = get_special_arg(args, 'secret')
  passwd = get_special_arg(args, 'password')
  
  puid = get_special_arg(args, 'puid', required=False)
  if not puid:
    PUIDS.load_from_gpg_file(args.puid_db, passwd)
    puid = PUIDS.get(hostname)
    if not puid: sys.exit('--puid not given and unable to entry entry for {hostname} in {args.puid_db}')

  os.environ['PUID'] = puid
  blob = KMC.generate_key_registration(
      keyname=keyname, key=secret, override_hostname=hostname,
      username=args.username, password=args.user_password, comment=args.comment)

  new_cnt = add_key_from_blob(blob, passwd, require(args, 'datafile'), args.force)
  print(f'ok: {args.datafile} now has {new_cnt} entries.')
  return 0

  
if __name__ == '__main__':
    sys.exit(main())

