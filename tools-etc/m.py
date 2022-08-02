#!/usr/bin/python3

'''run-time filesystem mounter

I generally use sshfs to mount remote filesystems, and encfs to provide
transparent encryption.  This tool provides simple and terse commands to
mount filesystems of both types.

It also supports dependency logic, i.e. if either the source or destination
moint-points for an encfs configuration are remote, the encfs config can
"need" the appropriate sshfs configs.

'''

import argparse, os, subprocess, sys
from collections import namedtuple

# ---------- types

Sshfs = namedtuple('sshfs_mounter',  'opts source')
Encfs = namedtuple('encfs_mounter',  'kmc_name encfs_dir')

Mp = namedtuple('mountpoint_config', 'name aliases source mp_needs mp_provides')
# mp.needs is a mountopint_config.name or None
# mp.provides is the target mount-point, and is a direcotry name relative to BASEDIR

# ---------- global config

#       name            aliases         source                                             needs      provides
CONFIGS = [
    Mp('share',         ['s'],          Sshfs('-p 222',  'jack:/home/ken/share'),          None,     'mnt/share'),
    Mp('default',       ['d'],          Encfs('default', 'mnt/share/encfs/default'),       'share',  'mnt/default'),
    Mp('home',          ['h'],          Encfs('home',    'mnt/share/encfs/home'),          'share',  'mnt/home'),
    Mp('private',       ['p'],          Encfs('private', 'mnt/share/encfs/private'),       'share',  'mnt/private'),
    # mm
    Mp('data1',         ['D'],          Sshfs('-p 222',  'jack:/data1'),                   'share',  'mnt/data1'),
    Mp('mov',           ['m'],          Encfs('mov',     'mnt/data1/mov'),                 'data1',  'mnt/mov'),
    Mp('bp',            ['b'],          Encfs('bp',      'mnt/data1/bp'),                  'data1',  'mnt/bp'),
    # jack
    Mp('jroot',         ['R'],          Sshfs('-r',      'j:/'),                           None,     'mnt/jroot'),
    Mp('html',          ['H'],          Sshfs('',        'j:/rw/dv/webdock/var_www/html'), None,     'mnt/html'),
    # a1
    Mp('aroot',         ['A'],          Sshfs('',        'a1:/'),                          None,     'mnt/aroot'),
]

BASEDIR = os.environ.get('BASEDIR', os.environ.get('HOME'))

# ---------- global state

ARGS = {}   # set by parse_args()


# ---------- helpers
# All functions that return strings return a human-readable error message or "None" if all is well,
# unless otherwise noted.

def check(dir: str) -> str:
    dir = d(dir)
    if not os.path.isdir(dir): return 'Dir not found: ' + dir
    if not os.listdir(dir): return 'No files in ' + dir
    return None

def d(dirname):
    if not dirname: return dirname
    return dirname if dirname.startswith('/') else os.path.join(BASEDIR, dirname)

def emit(s, ret='@return-s@') -> str:   # Returns "ret" param or "s" if "ret" not provided.
    print(s, file=sys.stderr)
    return s if ret == '@return-s@' else ret

def find_by_name(name) -> Mp:
    for c in CONFIGS:
        if c.name == name: return c
        for a in c.aliases:
            if a == name: return c
    return None

def needs_dir(config: Mp) -> str:  # Returns name of directory that config deps on.
    dep_config = find_by_name(config.mp_needs)
    return d(dep_config.mp_provides)


# ---------- business logic

def mount(config: Mp) -> str:
    if check(config.mp_provides) is None: return emit(config.name + ' already mounted', None)
    if config.mp_needs and check(needs_dir(config)) is not None:
        emit('%s needs %s' % (config.name, config.mp_needs))
        err = mount_by_name(config.mp_needs)
        if err: return err
        # Sometimes fulfilling a dep is sufficient.
        if check(config.mp_provides) is None: return emit(config.name + ' already mounted', None)
    if isinstance(config.source, Sshfs):
        cmd = ['/usr/bin/sshfs', config.source.opts, config.source.source, d(config.mp_provides)]
        if not cmd[1]: cmd.pop(1)
    elif isinstance(config.source, Encfs):
        cmd = ['/usr/bin/encfs', '--extpass', f'/usr/local/bin/kmc --km_cert "" encfs-{config.source.kmc_name}', d(config.source.encfs_dir), d(config.mp_provides)]
    else:
        return 'Unknown config.source type'
    if ARGS.allow_root: cmd.extend(['-o', 'allow_root'])
    subprocess.check_call(cmd)
    err = check(config.mp_provides)
    if err: return 'mount failed: ' + err
    emit(f'{config.name}: ok')
    return None


def mount_all() -> str:
    for c in CONFIGS:
        err = mount(c)
        if err and not 'already' in err: return err
    return emit('all ok', None)


def mount_by_name(name: str) -> str:
    cfg = find_by_name(name)
    if not cfg: return 'no config found for: ' + name
    return mount(cfg)


def tester():
    mounted = []
    unmounted = []
    for c in CONFIGS:
        if check(c.mp_provides) is None:
            mounted.append(c.name)
        else:
            unmounted.append(c.name)
    print(f'mounted: {mounted}\nnot mounted: {unmounted}')
    return len(mounted)


def unmounter():
    for c in reversed(CONFIGS):
        if check(c.mp_provides) is None:
            subprocess.check_call(['/usr/bin/fusermount', '-u', d(c.mp_provides)])
            if check(c.mp_provides) is None:
                emit(f'unmount of {c.name}: {c.mp_provides} failed.')
            else:
                emit(f'unmounted {c.name}')
    # Sometimes sshfs will auto-disconnect, leaving orphaned encfs mounts.
    # They don't get fixed above, as the dead connection failes check().
    for i in os.popen('/usr/bin/mount | /bin/grep encfs').read().split('\n'):
        if not i: continue
        mp = i.split(' ')[2]
        subprocess.check_call(['/usr/bin/fusermount', '-u', mp])
        emit(f'unmounted {mp}')


# ---------- main

def parse_args(argv):
  ap = argparse.ArgumentParser(description='authN token generator')
  ap.add_argument('--allow-root', '-A', action='store_true', help='allow root to access mounted filesystems')
  ap.add_argument('targets', nargs="*", help='list of mountpoint_config names (or aliases) to mount.  special targets: a=all, t=test, u=umount')
  return ap.parse_args(argv)


def main(argv=[]):
    global ARGS
    ARGS = parse_args(argv or sys.argv[1:])
    
    if not ARGS.targets: return mount_by_name('default')

    for arg in ARGS.targets:
        if arg in ['tester', 'test', 't']: tester()
        elif arg in ['umount', 'u', '0']: unmounter()
        elif arg in ['all', 'a', '1']: mount_all()
        else:
            err = mount_by_name(arg)
            if err: return emit(err, -1)


if __name__ == '__main__':
    sys.exit(main())
