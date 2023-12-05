#!/usr/bin/python3

'''run-time filesystem mounter

Simple and terse commands to mount filesystems of various types.

Supports dependency logic, i.e. if either the source or destination
moint-points for an encfs configuration are remote, the encfs config can
"need" the appropriate sshfs configs.

'''

import os, time, sys
from collections import namedtuple

import kcore.common as C

# ---------- types

Encfs = namedtuple('encfs_mounter',  'kmc_name encfs_dir')
Mount = namedtuple('mount_mounter',  'opts')
Rclon = namedtuple('rclone_mounter', 'opts source')
Sshfs = namedtuple('sshfs_mounter',  'opts source')

Mp = namedtuple('mountpoint_config', 'name aliases source mp_needs mp_provides')
# mp.needs is a mountopint_config.name or None
# mp.provides is the target mount-point, and is a direcotry name relative to BASEDIR

# ---------- global config

#       name            aliases         source                                             mp_needs  mp_provides
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
    Mp('jroot',         ['r'],          Sshfs('',        'j:/rw/root'),                    None,     'mnt/jroot'),
    Mp('jrootdir',      ['R'],          Sshfs('-r',      'j:/'),                           None,     'mnt/jrootdir'),
    Mp('html',          ['H'],          Sshfs('',        'j:/rw/dv/webdock/var_www/html'), None,     'mnt/html'),
    # a1
    Mp('aroot',         ['A'],          Sshfs('',        'a1:/'),                          None,     'mnt/aroot'),
    # steamdeck
    Mp('sdd',           ['S'],          Sshfs('',        'sdd:/run/media/mmcblk0p1'),      None,     'mnt/sdd'),
    Mp('sdh',           [],             Sshfs('',        'sdd:/home/deck'),                None,     'mnt/tmp'),
    # kasm
    Mp('d-b',           [],             Sshfs('',        'kasm://home/persist/chrome-b/ken-b/Downloads'),      None,     'mnt/d-b'),
    Mp('d-bbb',         [],             Sshfs('',        'kasm://home/persist/chrome-bbb/ken-bbb/Downloads'),  None,     'mnt/d-bbb'),
    # gdrive
    Mp('gdrive',        ['g'],          Rclon('--read-only', 'gdrive-ro:/'),               None,     'mnt/gdrive'),
    # ext
    #Mp('ext',           ['e'],          Mount(None),                                       None,      '/mnt/ext'),
    #Mp('ext-encfs',     ['ee'],         Encfs('ext',     '/mnt/ext/encfs'),                'ext',     '/mnt/ext/efs'),
]

BASEDIR = os.environ.get('BASEDIR', os.environ.get('HOME'))

# ---------- global state

ARGS = {}   # set by parse_args()


# ---------- helpers
# All functions that return strings return a human-readable error message or "None" if all is well,
# unless otherwise noted.

# replaced by is_mountpoint()
#def check(dir: str) -> str:
#    dir = d(dir)
#    if not os.path.isdir(dir): return 'Dir not found: ' + dir
#    if not os.listdir(dir): return 'No files in ' + dir
#    return None

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

def is_mountpoint(dir: str) -> bool:
    rslt = run(['/usr/bin/mountpoint', '-q', d(dir)])
    return rslt.ok

def needs_dir(config: Mp) -> str:  # Returns name of directory that config deps on.
    dep_config = find_by_name(config.mp_needs)
    return d(dep_config.mp_provides)

def run(cmd, env=None):
    if ARGS.verbose: print(f'[verbose] running: {cmd}', file=sys.stderr)
    rslt = C.popen(cmd, env=env)
    if ARGS.verbose: print(f'[verbose] command returned: {rslt}', file=sys.stderr)
    return rslt

def smartappend(target_list, item):
    if not item: return target_list
    target_list.extend(item if type(item) == list else [item])
    return target_list


# ---------- business logic

def mount(config: Mp) -> str:
    env = None
    if is_mountpoint(config.mp_provides): return emit(config.name + ' already mounted', None)
    if config.mp_needs and not is_mountpoint(needs_dir(config)):
        emit('%s needs %s' % (config.name, config.mp_needs))
        err = mount_by_name(config.mp_needs)
        if err: return err
        # Sometimes fulfilling a dep is sufficient.
        if is_mountpoint(config.mp_provides): return emit(config.name + ' already mounted', None)
    if isinstance(config.source, Encfs):
        cmd = ['/usr/bin/encfs', '--extpass', f'/usr/local/bin/kmc --km_cert "" encfs-{config.source.kmc_name}', d(config.source.encfs_dir), d(config.mp_provides)]
    elif isinstance(config.source, Mount):
        cmd = ['/usr/bin/mount']
        smartappend(cmd, config.source.opts)
        cmd.append(d(config.mp_provides))
    elif isinstance(config.source, Rclon):
        if 'RCLONE_CONFIG_PASS' not in os.environ:
            env = dict(os.environ)
            env['RCLONE_CONFIG_PASS'] = C.popener(['/usr/local/bin/kmc', '--km_cert', '', 'rclone'])
        cmd = ['/usr/bin/rclone', 'mount']
        smartappend(cmd, config.source.opts)
        cmd.extend(['--daemon', config.source.source, d(config.mp_provides)])
    elif isinstance(config.source, Sshfs):
        cmd = ['/usr/bin/sshfs']
        smartappend(cmd, config.source.opts)
        cmd.extend([config.source.source, d(config.mp_provides)])
        if not cmd[1]: cmd.pop(1)
    else:
        return f'Unknown config.source type: {type(config.source)}'

    if ARGS.allow_root: cmd.extend(['-o', 'allow_root'])
    out = run(cmd, env)
    time.sleep(0.5)
    is_mp = is_mountpoint(d(config.mp_provides))
    if not out.ok or not is_mp: return f'mount failed for {config.name}: {out.out}'
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


def get_mounted():
    mounted = []
    unmounted = []
    for c in CONFIGS:
        if is_mountpoint(c.mp_provides):
            mounted.append(c.name)
        else:
            unmounted.append(c.name)
    return mounted, unmounted


def list_mounted():
    mounted, unmounted = get_mounted()
    print(f'mounted: {mounted}\nnot mounted: {unmounted}')
    return len(mounted)


def unmounter(force=False):
    for c in reversed(CONFIGS):
        if is_mountpoint(c.mp_provides):
            if isinstance(c.source, Mount):
                cmd = ['/usr/bin/umount']
                if force: cmd.append('-l')
                cmd.append(d(c.mp_provides))
                out = run(cmd)
            else:
                cmd = ['/usr/bin/fusermount']
                if force: cmd.append('-z')
                cmd.extend(['-u', d(c.mp_provides)])
                out = run(cmd)
            is_mp = is_mountpoint(c.mp_provides)
            if not out.ok or is_mp:
                emit(f'unmount of {c.name}:{c.mp_provides} failed: {out.out}')
            else:
                emit(f'unmounted {c.name}')


# ---------- GUI

def show_gui():
    cmd = ['zenity', '--width', '400', '--height', '650', '--title', 'mounter', '--list', '--column', 'alias', '--column', 'name', '--column', 'on?', '--column', 'provides']
    mounted, unmounted = get_mounted()
    for cfg in CONFIGS:
        cmd.extend([cfg.aliases[0] if cfg.aliases else '',
                    cfg.name,
                    'X' if cfg.name in mounted else '',
                    cfg.mp_provides])
    cmd.extend(['a', 'all', '', ''])
    cmd.extend(['u', 'unmount', '', ''])
    sel = C.popener(cmd)
    if not sel or sel.startswith('ERR'): sys.exit(0)
    return [sel]


# ---------- main

def parse_args(argv):
    extra = 'Available targets:\n\n' + '\n'.join([f'   {c.name:<12}\t{c.aliases}\t{c.mp_provides}' for c in CONFIGS])
    ap = C.argparse_epilog(description='authN token generator', epilog_extra=extra)
    ap.add_argument('--allow-root', '-A', action='store_true', help='allow root to access mounted filesystems')
    ap.add_argument('--verbose', '-v',    action='store_true', help='show executed commands')
    ap.add_argument('targets', nargs="*", help='list of mountpoint_config names (or aliases) to mount.  special targets: a=all, t=test, u=umount, fu=force-umount')
    return ap.parse_args(argv)


def main(argv=[]):
    global ARGS
    ARGS = parse_args(argv or sys.argv[1:])

    if not ARGS.targets: ARGS.targets = show_gui()

    for arg in ARGS.targets:
        if arg in ['list', 'L', 'tester', 'test', 't']: list_mounted()
        elif arg in ['umount', 'u', 'fu', '0']: unmounter(arg=='fu')
        elif arg in ['all', 'a', '1']: mount_all()
        else:
            err = mount_by_name(arg)
            if err: return emit(err, -1)


if __name__ == '__main__':
    sys.exit(main())
