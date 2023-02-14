#!/usr/bin/python3
'''simple wrapper around Python symmetric encrpytion.

If detects already encrypted data, this will decrypt it.  Otherwise, it encrypts.
'''

import sys

import kcore.common as C
import kcore.uncommon as UC


def parse_args(argv):
  ap = C.argparse_epilog()
  ap.add_argument('--infile',   '-i', default=None, help='(deprecated; use non-flag value instead.)  file to encrypt or decrypt')
  ap.add_argument('--out',      '-o', default=None, help='file to output to; use "-") for stdout; default will either add or remove a .pcrypt suffix from infile, as appropriate.')
  ap.add_argument('--password', '-p', default='-', help='password to encrypt/decrypt with.  - to read from tty, $X to read from environment varaible X.')
  ap.add_argument('--salt',     '-s', default='',  help='Used to help translate your password into a secure encryption key.  Similar to the password, must be the same for encryption and decryption, although can be safely reused between messages with difference passwords.  Optional; the underlying library will use a default if you dont provide one.')
  ap.add_argument('input_file',default=None,  nargs='?',  help='filename of input to encrypt or decrypt.  Default will read from stdin.')
  return ap.parse_args(argv)


def main(argv=[]):
  args = parse_args(argv or sys.argv[1:])
  pswd = C.resolve_special_arg(args, 'password')
  salt = C.resolve_special_arg(args, 'salt', required=False)

  infile = args.input_file or args.infile or '-'
  if args.out:
    outfile = args.out
  elif infile != '-':
    outfile = infile.replace('.pcrypt', '') if infile.endswith('.pcrypt') else infile + '.pcrypt'
  else:
    outfile = '-'

  data = C.read_file(infile)
  if not data: sys.exit(f'unable to open input file {args.infile}')
  if data.startswith('ERROR'): sys.exit(data)

  output = UC.symmetric_crypt(data, pswd, salt)
  if output.startswith('ERROR'): sys.exit(output)
  C.write_file(outfile, output)


if __name__ == '__main__':
    sys.exit(main())
