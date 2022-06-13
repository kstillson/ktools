#!/usr/bin/python3
'''simple wrapper around gpg symmetric encrpytion.

The main purpose of this is to avoid the use of gpg-agent for entering the
encryption passphrase.  The passphrase can be entered directly on the
command-line, through stdin (which gpg-agent doesn't support) or via an
environment variable.

In-fact, this tool will attempt to kill the gpg-agent if it appears to have been
started up because of this tool's calling out to GPG.

<rant> Once upon a time, I used GPG symmetric encryption for almost all my
secrets that needed to be accessed by automated systems.  However, I've gotten
more and more frustrated with how difficult GPG makes this, and so eventually
migrated over to ../tools/pcrypt.py, which provides a CLI for
../kcore/uncommon.py:symmetric_crypt(), which is a trivial wrapper for
Python's "batteries-included" symmetric encryption.  This avoids the somewhat
inelegant shelling-out to call the gpg CLI, and completely avoids all the
unnecessary and ever-changing junk that GPG has accumulated over time.</rant>

'''

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

