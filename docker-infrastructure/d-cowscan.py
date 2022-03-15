#!/usr/bin/python

import argparse, datetime, glob, os, socket, subprocess

DLIB = "/var/lib/docker/200000.200000"
HOSTNAME = socket.gethostname()
PROBLEMS = 0
SAW_TOKEN = False
TOKEN = str(datetime.datetime.now())
TOKEN_CONTAINER = 'mysql-a' if HOSTNAME.startswith('a2') else 'eximdock'
TOKEN_FILE = '/tmp/.stamp'

IGNORE_LIST = [
    'dbg-',
    '.pid',
    '.pyc',
    'blender:/root/.config/pulse/blender-runtime',
    'dev:/',
    'insyncdock:/root/.gtk-bookmarks',
    'insyncdock:/tmp/insync0.sock',
    'insyncdock:/tmp/tmp',
    'insyncdock:/var/spool/cron/cron',
    'kmdock:/home/km/.gnupg/pubring.kbx',
    'mysqldock:/run/mysqld/mysqld.sock',
    'mysql-a:/run/mysqld/mysqld.sock',
    'nagdock:/tmp/x',
    'privdock:/tmp/sess_',
    'privdock:/tmp/twig/',
    'rclonedock-dbg:/',
    'rclonedock:/root/.cache/rclone',
    'rclonedock:/root/.config/rclone/rclone.conf',
    'rsnapdock:/etc/rsnapshot',
    'rsnapdock:/root/.bashrc',
    'rsnapdock:/root/.ssh',
    'sambadock:/etc/samba/private/passdb.tdb',
    'sambadock:/var/cache/samba/',
    'sambadock:/var/lib/samba/',
    'sshdock:/var/log/rootsh/ken.',
    'syslogdock:/run/syslog-ng.ctl',
    'syslogdock:/run/syslog-ng.persist',
    'webdock:/tmp/sess_',
    'webdock:/tmp/pb.rl',
]

# ----------
# docker general


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
    if container == TOKEN_CONTAINER and path == TOKEN_FILE:
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


def write_token():
    subprocess.check_call(['/usr/bin/docker', 'exec', '-u', '0', TOKEN_CONTAINER, '/bin/bash', '-c', 'echo "%s" > %s' % (TOKEN, TOKEN_FILE)])


# ----------
# main

def main():
    global ARGS
    ap = argparse.ArgumentParser(description='docker container launcher')
    ap.add_argument('--debug', '-d', default=0, type=int, help='debug level, 0-3')
    ap.add_argument('--rm', '-R', action='store_true', help='remove offending files rather than just printing them.')
    ARGS = ap.parse_args()

    write_token()

    for temp in subprocess.check_output(['/usr/bin/docker', 'ps', '--format', '{{.Names}} {{.ID}}']).split('\n'):
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

    if not SAW_TOKEN: problem(TOKEN_FILE, 'failed to see correctly set token file')

    if PROBLEMS == 0: print('all ok')


if __name__ == "__main__":
  main()

