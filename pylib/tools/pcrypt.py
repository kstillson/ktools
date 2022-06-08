#!/usr/bin/python3
'''simple wrapper around Python symmetric encrpytion'''

import argparse, getpass, os, signal, sys

import kcore.common as C
import kcore.uncommon as UC

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



# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument('--encrypt', '-e', action='store_true', help='@@')
  ap.add_argument('--infile', '-i', default='-', help='@@')
  ap.add_argument('--out', '-o', default='-', help='@@')
  ap.add_argument('--password', '-p', default='-', help='password to encrypt/decrypt with.  - to read from stdin, $X to read from environment varaible X.')
  ap.add_argument('--salt', '-s', default='AUTO', help='@@')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  pswd = get_special_arg(args, 'password')
  salt = get_special_arg(args, 'salt', required=False)
  if salt == 'AUTO': salt = os.environ.get('PUID', 'its-bland-without-salt')
  
  data = C.read_file(args.infile)
  if not data: sys.exit('No input data found')

  output = UC.encrypt(data, pswd, salt) if args.encrypt else UC.decrypt(data, pswd, salt)

  if args.out == '-':
      print(output)
  else:
      with open(args.out, 'w') as f: f.write(output)
  return 0


if __name__ == '__main__':
    sys.exit(main())

