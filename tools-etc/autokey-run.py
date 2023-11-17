#!/usr/bin/python3

'''autokey selector

List all (or filtered) available autokey selections.
The selected one is executed and its output loaded into the copy/paste buffer.
'''

import glob, json, os, subprocess, sys
import kcore.common as C
import kcore.uncommon as UC

DEBUG = False


# ---------- msgs

def debug(msg):
    if DEBUG: print(msg)


# ---------- business logic

class Scanner:
    '''Recursive scan for files (optionally matching a filter), starting from the given dir'''

    def __init__(self, filter=None):      # filter is applied against the shortened names...
        self._db = {}                     # maps shortened names to full pathnames
        self._filter = filter
        self._counter = 0

    def shorten(self, name):
        '''General a friendly short name (the ones that will display on the selection list) from a full pathname.'''
        parts = name.split('/')
        fullname = parts.pop()
        basename, ext = os.path.splitext(fullname)
        lastdir = ('  (' + parts.pop() + '/)') if parts else ''
        answer = f'{self._counter:02} {basename}{lastdir}'
        self._counter += 1
        return answer

    def scan(self, dirname):
        for i in glob.glob(os.path.join(dirname, '*')):
            path = os.path.join(dirname, i)
            if os.path.isdir(path): self.scan(path)
            else:
                short = self.shorten(path)
                if self._filter and self._filter not in short: continue
                self._db[short] = path
        return self._db              # returns accumulated dict


def to_clip(data):
    C.popen(['/usr/bin/xclip', '-selection', 'clipboard', '-i'], stdin_str=data, timeout=1, passthrough=True)


def select_autokey(args):
    with open(os.path.expanduser('~/.config/autokey/autokey.json')) as f: cfg = json.load(f)
    dirs = cfg['folders']

    scanner = Scanner(filter=args.search)
    for dirname in dirs: db = scanner.scan(dirname)

    size = len(db)
    if size == 0: C.zfatal('found no matching autokeys')
    if size == 1:
        sel = next(iter(db.keys()))
        debug(f'autoselected {sel}')
    else:
        sel = C.popener(['/usr/bin/zenity', '--list', '--column', 'autokey to put into run/copy', '--width', '450', '--height', str(80 + 40 * size)] + sorted(db.keys()))
    if 'ERROR' in sel: C.zfatal('aborted')

    fullpath = db.get(sel)
    if not fullpath: C.zfatal(f'unable to find entry {sel}')
    debug(f'selected autokey file {fullpath}')

    return fullpath


 # ---------- main

def parse_args(argv):
    ap = C.argparse_epilog(description='otp generator')
    ap.add_argument('search', nargs='?',  default='',          help='substring of autokey to search for')
    ap.add_argument('--debug', '-d',      action='store_true', help='print debugging info')
    return ap.parse_args(argv)


def main(argv=[]):
    args = parse_args(argv or sys.argv[1:])
    if args.debug:
        global DEBUG
        DEBUG = True

    fullpath = select_autokey(args)
    content = C.read_file(fullpath)
    if not content: C.zfatal(f'unable to read content of {fullpath}')

    basename, ext = os.path.splitext(fullpath)
    if ext == '.txt':
        to_clip(content)
        C.zinfo(f'copied contents of {basename}')

    elif ext == '.py':
        content = content.replace('keyboard.send_keys', 'print')
        with UC.Capture() as cap:
            debug(f'executing: {content}')
            exec(content)
            to_clip(cap.out)
            if cap.err: C.zwarn(f'command error: {cap.err}')
            else:
                if cap.out: C.zinfo(f'copied output: {cap.out[:10]}...')

    else: C.zfatal(f'unknown expansion type: "{ext}" in {fullpath}')


if __name__ == '__main__': sys.exit(main())
