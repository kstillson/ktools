#!/usr/bin/python3
'''simple wrapper around gpg symmetric encrpytion'''

import argparse, os, signal, sys

import kcore.uncommon as UC

# ---------- helpers

def pgrep(srch='gpg-agent'):
    return set(UC.popener(['pgrep'], srch).split('\n'))


# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument('--password', '-p', default='-', help='password to encrypt/decrypt with.  - to read from stdin, $X to read from environment varaible X.')
  ap.add_argument('filename', help='Name of file to encrypt/decrypt.  Which to do is driven by whether file has .gpg extension')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])

  gpg_pids_initial = pgrep()

  pswd = UC.resolve_special_arg(args, 'password')
  with open(args.filename) as f: blob = f.read()
  decrypt = '.gpg' in args.filename

  blob2 = UC.gpg_symmetric(blob, pswd, decrypt)
  if blob2.startswith('ERROR'): sys.exit(blob2)

  outname = args.filename.replace('.gpg', '') if decrypt else args.filename + '.gpg'
  with open(outname, 'w') as f: f.write(blob2)

  gpg_pids_final = pgrep()
  for pid in gpg_pids_final - gpg_pids_initial:
      os.kill(int(pid), signal.SIGTERM)

  return 0


if __name__ == '__main__':
    sys.exit(main())

