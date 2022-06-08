#!/usr/bin/python3
'''simple wrapper around Python symmetric encrpytion.

If detects already encrypted data, this will decrypt it.  Otherwise, it encrypts.
'''

import argparse, sys

import kcore.common as C
import kcore.uncommon as UC


ENCRYPTION_PREFIX = 'pcrypt1:'   # used to auto-detect whether to encrypt or decrypt


def parse_args(argv):
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument('--infile',   '-i', default='-', help='file to encrypt or decrypt; default ("-") will read from stdin')
  ap.add_argument('--out',      '-o', default='-', help='file to output to; default ("-") will send to stdout')
  ap.add_argument('--password', '-p', default='-', help='password to encrypt/decrypt with.  - to read from tty, $X to read from environment varaible X.')
  ap.add_argument('--salt',     '-s', default='',  help='Used to help translate your password into a secure encryption key.  Similar to the password, must be the same for encryption and decryption, although can be safely reused between messages with difference passwords.  Optional; the underlying library will use a default if you dont provide one.')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])
  pswd = UC.resolve_special_arg(args, 'password')
  salt = UC.resolve_special_arg(args, 'salt', required=False)
  data = C.read_file(args.infile)
  if data.startswith('ERROR'): sys.exit(data)

  decrypt = data.startswith(ENCRYPTION_PREFIX)
  if decrypt: data = data.replace(ENCRYPTION_PREFIX, '')

  output = UC.symmetric_crypt(data, pswd, salt, decrypt)
  if output.startswith('ERROR'): sys.exit(output)

  if not decrypt: output = ENCRYPTION_PREFIX + output
  C.write_file(args.out, output)


if __name__ == '__main__':
    sys.exit(main())
