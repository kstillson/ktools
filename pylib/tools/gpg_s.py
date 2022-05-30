#!/usr/bin/python3
'''simple wrapper around gpg symmetric encrpytion'''

import argparse, getpass, os, signal, subprocess, sys

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


def pgrep(srch='gpg-agent'):
    p = subprocess.Popen(['pgrep', srch], stdout=subprocess.PIPE)
    out, _ = p.communicate()
    return out.decode().strip()


# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument('--password', '-p', default='-', help='password to encrypt/decrypt with.  - to read from stdin, $X to read from environment varaible X.')
  ap.add_argument('filename', help='Name of file to encrypt/decrypt.  Which to do is driven by whether file has .gpg extension')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  gpg_pid_initial = pgrep()

  pswd = get_special_arg(args, 'password')
  with open(args.filename) as f: blob = f.read()
  decrypt = '.gpg' in args.filename

  blob2 = UC.gpg_symmetric(blob, pswd, decrypt)
  if blob2.startswith('ERROR'): sys.exit(blob2)

  outname = args.filename.replace('.gpg', '') if decrypt else args.filename + '.gpg'
  with open(outname, 'w') as f: f.write(blob2)

  gpg_pid_final = pgrep()
  if gpg_pid_final and not gpg_pid_initial: os.kill(int(gpg_pid_final), signal.SIGTERM)

  return 0


if __name__ == '__main__':
    sys.exit(main())

