#!/usr/bin/python3
'''
TODO(doc)

TODO: move the IGNORE_LIST to a config file.
'''

import argparse, datetime, glob, os, socket
import kcore.uncommon as UC

# ---------- global controls

DLIB = os.environ.get('DLIB', '/var/lib/docker/200000.200000')


# ---------- global state

ARGS = {}
HOSTNAME = socket.gethostname()
PROBLEMS = 0
SAW_TOKEN = False
TOKEN = str(datetime.datetime.now())

# This list will be appended with the contents of
# private.d/d-cowscan.ignore:IGNORE_LIST .  See the --private flag.

IGNORE_LIST = [
    'dbg-',
    '.pid',
    '.pyc',
    'nagdock:/tmp/x',
    'rclonedock-dbg:/',
    'rclonedock:/root/.cache/rclone',
    'rclonedock:/root/.config/rclone/rclone.conf',
    'rsnapdock:/etc/rsnapshot',
    'rsnapdock:/root/.bashrc',
    'rsnapdock:/root/.ssh',
    'syslogdock:/run/syslog-ng.ctl',
    'syslogdock:/run/syslog-ng.persist',
    'webdock:/tmp/pb.rl',
]


# ----------
# general

def read_file(filename):
    with open(filename) as r: return r.read()

def resolve_glob(pattern):
    matches = glob.glob(pattern)
    if len(matches) != 1: raise Exception('glob failed to resolve %s -> %s' % (pattern, matches))
    return matches[0]

# ----------
# cow specific

def check(container, real_root, root, name):
    global SAW_TOKEN
    path = os.path.join(root, name)
    full_path = os.path.join(real_root, name)
    spec = '%s:%s' % (container, path)
    if ARGS.debug >= 3: print('DEBUG checking: %s (%s)' % (spec, full_path))

    # Special logic for the token file.
    if container == ARGS.token_container and path == ARGS.token_file:
        token_contents = read_file(os.path.join(real_root, name)).rstrip()
        if token_contents == TOKEN:
            SAW_TOKEN = True
            if ARGS.debug: print('token contents ok')
            return True
        else:
            return problem(spec, 'unexpected token contents (%s != %s)' % (token_contents, TOKEN))

    # Check the ignore list.
    for i in IGNORE_LIST:
        if i in spec:
            if ARGS.debug >= 2: print('ok (ignore list): %s' % spec)
            return True

    # If we get to here, we've got an unexpected file.
    if ARGS.rm:
        print('rm %s' % spec)
        os.unlink(full_path)
        return False
    else:
        return problem(spec, 'unexpected file')


def problem(filespec, msg):
    global PROBLEMS
    PROBLEMS += 1
    print('%s: %s' % (msg, filespec))
    return False


def load_ignore_list(privfile):
    if not privfile: return
    privfile_orig = privfile
    if not os.path.isfile(privfile):
        privfile = os.path.join(os.path.dirname(__file__), privfile_orig)
    if not os.path.isfile(privfile):
        privfile = os.path.join('private.d', privfile_orig)
    if not os.path.isfile(privfile):
        return problem(privfile, 'unable to load --private ignore list')
    global IGNORE_LIST
    addl = UC.load_file_as_module(privfile)
    IGNORE_LIST.extend(addl.IGNORE_LIST)
    if ARGS.debug > 0: print(f'Added {len(addl.IGNORE_LIST)} ignore items from {privfile}')


def write_token():
    UC.popen(['/usr/bin/docker', 'exec', '-u', '0', ARGS.token_container, '/bin/bash', '-c', 'echo "%s" > %s' % (TOKEN, ARGS.token_file)])


# ----------
# main

def main():
    ap = argparse.ArgumentParser(description='docker container launcher')
    ap.add_argument('--debug', '-d',     default=0, type=int, help='debug level, 0-3')
    ap.add_argument('--private', '-p',   default='d-cowscan.ignore', help='file with additional IGNORE_LIST contents')
    ap.add_argument('--rm', '-R',        action='store_true', help='remove offending files rather than just printing them.')
    ap.add_argument('--token_container', default='eximdock', help='name of container into which to induce a change to make sure we detect it')
    ap.add_argument('--token_file',      default='/tmp/.stamp', help='name of file for induced change')
    global ARGS
    ARGS = ap.parse_args()

    load_ignore_list(ARGS.private)
    write_token()

    for temp in UC.popener(['/usr/bin/docker', 'ps', '--format', '{{.Names}} {{.ID}}']).split('\n'):
        if not temp: continue
        container, id_prefix = temp.split(' ')
        mount_id = read_file(resolve_glob(DLIB + '/image/overlay2/layerdb/mounts/%s*/mount-id' % id_prefix))
        cow_dir = DLIB + '/overlay2/%s/diff' % mount_id
        if ARGS.debug: print('DEBUG: working on %s -> %s' % (container, cow_dir))
        for real_root, dirs, files in os.walk(cow_dir):
            root = real_root[len(cow_dir):]
            for f in files:
                check(container, real_root, root, f)

    if ARGS.rm: return 0

    if not SAW_TOKEN: problem(ARGS.token_file, 'failed to see correctly set token file')

    if PROBLEMS == 0: print('all ok')


if __name__ == "__main__":
  main()

