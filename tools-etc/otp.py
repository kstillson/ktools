#!/usr/bin/python3

'''OTP retriever

This is a frontend to oauthtool totp generation, used to basically reimplemnt
Google Authenticator.

Note that this allows OTP generation without a physically separate device,
which is a bit contrary to the spirit of multi-factor authentication.  It's
still "something you have" as opposed to "something you know" (you don't know
the OTP values this will generate until you generate them, and what you have
is this OTP generator and its encrypted database).  But assuming this program
is run on the same device as where you are logging in, an attacker with access
to that device has access to both factors- which they wouldn't if the OTP was
generated on a physically separate phone.

To exact an OTP secret from a QR code, use https://github.com/scito/extract_otp_secrets.git :
  zbarimg {qrcode.png} > qrcode.url
  python extract_otp_secrets.py --no-color -v --csv - qrcode1.url

Accumulated secrets are stored in a pcrypt-encrypted csv file.
The decryption password for that file is kept in a gnome keyring.

The non-flag arguments to this script form a search string, which is matched
against all the fields in the csv file.  If a single match comes up, it is
used automatically.  If more than one match is found, a menu is presented for
the user to select which one they want.

The resulting generated OTP is copied into the x11 copy-paste buffer.

'''

import subprocess, sys
from collections import namedtuple

import kcore.common as C
import kcore.uncommon as UC
import ktools.kmc as KMC


# ---------- types

Otpdata = namedtuple('OTP_secret_entry', 'name secret issuer type counter url')
#
# Note: only the "secret" field is used for totp generation; the other fields
# are all metadata available for searching / filtering.


# ---------- msgs

def zmsg(msg, type='info', timeout=1, background=True):
    print(msg, file=sys.stderr)
    # external timeout (rather than zenity flag) for fractional values.
    cmd = ['/usr/bin/timeout', str(timeout), '/usr/bin/zenity', f'--{type}', '--text', msg]
    return subprocess.Popen(cmd) if background else C.popen(cmd)

def info(msg, timeout=1): return zmsg(msg, timeout=timeout)

def fatal(msg):
    zmsg(msg, type='error', timeout=4, background=True)
    sys.exit(-1)


# ---------- main


def parse_args(argv):
    ap = C.argparse_epilog(description='otp generator')
    ap.add_argument('otp', nargs='?',  default='',          help='substring of otp value to retrieve')

    g1 = ap.add_argument_group('launch options')
    ap.add_argument('--out',     '-o', action='store_true', help='output value to stdout rather than copying to x clipboard')

    g2 = ap.add_argument_group('advanced')
    g2.add_argument('--db',            default='/home/ken/.local/otp.csv.pcrypt',  help='path to pcrypt-encrypted totp secrets')
    g1.add_argument('--kmc',           default='pcrypt-otp',                       help='name of key to retrieve from keymaster for unlocking OTP db')

    return ap.parse_args(argv)


def main(argv=[]):
    args = parse_args(argv or sys.argv[1:])

    if args.kmc:
        pcrypt_password = KMC.query_km(args.kmc)
        if not pcrypt_password: fatal('failed to get pcrypt decryption password')

        db_crypted = C.read_file(args.db)
        if not db_crypted: fatal(f'unable to read encrypted otp secrets database {args.db}')

        db_csv = UC.symmetric_crypt(db_crypted, pcrypt_password)
        if not db_csv: fatal(f'unable to decrypt {args.db}')

    else: db_csv = C.read_file(args.db)

    otp_db = []
    for line in db_csv.split('\n'):
        if not line or line.startswith('#') or line.startswith('name,'): continue
        fields = line.split(',')
        otp_db.append(Otpdata(*fields))
    if len(otp_db) == 0: fatal('no fields parsed from decrypted otp data')

    found = []
    for i in otp_db:
        if args.otp.lower() in i.name.lower(): found.append(i)

    if len(found) == 0: fatal(f'No entries matching "{args.otp}" found (searched {len(otp_db)} entries)')
    elif len(found) == 1:
        secret = found[0].secret
    else:
        # Multiple secrets matched; ask user which one they want.
        found.sort()
        sel = C.popener(['/usr/bin/zenity', '--list', '--column', 'OTP to generate', '--width', '450', '--height', str(80 + 40 * len(found))] + [f'{i.name} ({i.issuer})' for i in found])
        if 'ERROR' in sel: fatal('aborted')
        sel, _ = sel.split(' (', 1)
        for i in found:
            if i.name == sel:
                secret = i.secret
                break
        else:
            fatal(f'unable to find {sel} in matched names.. ?!')

    otp = C.popener(['/usr/bin/oathtool', '-b', '--totp', '-'], stdin_str=secret)

    if args.out:
        print(otp)
    else:
        C.popen(['/usr/bin/xclip', '-selection', 'clipboard', '-i'], stdin_str=otp, timeout=1, passthrough=True)
        info('copied', timeout=0.7)


if __name__ == '__main__': sys.exit(main())
