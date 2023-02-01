#!/usr/bin/python3

'''Launch a container.

This scripts constructs the command-line parameters for Docker to launch a
container.

Most settings can come from multiple sources, the priority order is:
  command-line flag, then
  settings file, then
  environment variable, then
  a hard-coded "fallback" value

See Readme-settings.yaml.md for a detailed description of the settings file.

'''

import argparse, glob, os, shutil, socket, subprocess, sys, yaml
from dataclasses import dataclass
from pathlib import Path

import kcore.auth as A


# ---------- local types

DEBUG = False

@dataclass
class Ctrl:
    control_name: str
    override_flag: str
    override_env: str
    setting_name: str
    test_mode_default: str
    normal_mode_default: str
    doc: str

    def __post_init__(self):
        self.resolved = None
        
    def debug(self, val, src):
        if DEBUG: err(f'resolved setting "{self.control_name}" \t to \t "{val}" \t from {src}')
        return val

    def resolve(self, args, basedir, settings, test_mode, dev_mode):
        if self.resolved: return self.resolved
        self.resolved = self._resolve(args, basedir, settings, test_mode, dev_mode)
        return self.resolved
    
    def _resolve(self, args, basedir, settings, test_mode, dev_mode):
        if self.override_flag:
            attrname = self.override_flag.replace('--', '').replace('-', '_')
            tmp = getattr(args, attrname, None)
            if tmp: return self.debug(tmp, 'override flag')

        if self.override_env:
            tmp = os.environ.get(self.override_env, None)
            if tmp: return self.debug(tmp, 'override env')

        if dev_mode:
            tmp = settings.get('dev_' + self.setting_name, None)
            if tmp: return self.debug(tmp, f'dev_{self.setting_name} from settings file')
        elif test_mode:
            tmp = settings.get('test_' + self.setting_name, None)
            if tmp: return self.debug(tmp, f'test_{self.setting_name} from settings file')
        tmp = settings.get(self.setting_name, None)
        if tmp: return self.debug(tmp, 'settings file')

        if test_mode:
            tmp = self.test_mode_default
            if dev_mode: tmp = tmp.replace('test', 'dev')
        else: tmp = self.normal_mode_default
        if not tmp: return self.debug(tmp, 'default value (which is None for this mode)')
        tmp = tmp.replace('@basedir', basedir)
        if not tmp.startswith('$'): return self.debug(tmp, 'mode default')
        tmp2 = os.environ.get(tmp[1:], None)
        return self.debug(tmp2, f'mode default via {tmp}')


# ---------- control constants

CONTROLS = [
#        control name,   override_flag,    override_env,             setting_name,  test-mode-default, normal default     doc
    Ctrl('autostart',    None,             None,                     'autostart',   None,              None,              'string indicating startup wave to auto-launch this container system system boot. Not used by this script.'),
    Ctrl('command',      None,             None,                     'cmd',         None,              None,              'send this as the command to run within the container. If an entrypoint is in use, this because params to that entrypoint (i.e. same as --extra-init)'),
    Ctrl('docker_exec',  '--docker-exec',  'DOCKER_EXEC',            'docker_exec', '/usr/bin/docker', '/usr/bin/docker', 'container manager to use (docker or podman)'),
    Ctrl('env',          '--env',          None,                     'env',         None,              None,              'list of {name}={value} pairs to set in environment within the container'),
    Ctrl('extra_docker', None,             None,                     'extra_docker',None,              None,              'list of additional command line arguments to send to the container launch CLI'),
    Ctrl('extra_init',   '--extra-init',   None,                     'extra_init',  None,              None,              'list of additional arguments to pass to the init command within the container'),
    Ctrl('foreground',   '--fg',           None,                     'foreground',  '1',               '0',               'set to "1" to run container in foreground with interactive/pty settings'),
    Ctrl('hostname',     '--hostname',     'KTOOLS_DRUN_HOSTNAME',   'network',     'test-@basedir',   '@basedir',        'host name to assign within the container'),
    Ctrl('image',        '--image',        None,                     'image',       '@basedir',        '@basedir',        'name of the image to launch'),
    Ctrl('ip',           '--ip',           'KTOOLS_DRUN_IP',         'ip',          '0',               '-',               'IP address to assign container.  Use "-" for dns lookup of container\'s hostname.  Use "0" (or dns failure) for auto assignment'),
    Ctrl('ipv6_ports',   None,             None,                     'ipv6_ports',  '0',               '0',               'if "1", enable IPv6 port mappings.'),
    Ctrl('log',          '--log',          'KTOOLS_DRUN_LOG',        'log',         'none',            '-',               'log driver for stdout/stderr from the container.  p/passthrough, j/journald, J/json, s/syslog[:url]'),
    Ctrl('ports',        '--ports',        None,                     'ports',       None,              None,              'list of {host}:{container} port pairs for mapping'),
    Ctrl('puid',         '--puid',         'PUID',                   'puid',        'auto',            'auto',            'if not "auto", pass the given value into $PUID inside the container.  "auto" will generate a consistent container-specific value.  Blank to disable.'),
    Ctrl('name',         '--name',         'KTOOLS_DRUN_NAME',       'name',        'test-@basedir',   '@basedir',        'name to assign to the launched container'),
    Ctrl('network',      '--network',      None,                     'network',     '$KTOOLS_DRUN_TEST_NETWORK', '$KTOOLS_DRUN_NETWORK',  'container network to use'),
    Ctrl('repo1',        '--repo',         'KTOOLS_DRUN_REPO',       'repo1',       'ktools',          'ktools',          'first repo to try for a matching image'),
    Ctrl('repo2',        '--repo2',        'KTOOLS_DRUN_REPO2',      'repo2',       None,              None,              'second repo to try for a matching image'),
    Ctrl('rm',           '--rm',           None,                     'rm',          '1',               '1',               'if set to "1", pass --rm to container manager, which clears out container remanants (e.g. json logs) upon exit'),
    Ctrl('tag',          '--tag',          'KTOOLS_DRUN_TAG',        'tag',         'latest',          'live',            'tagged or other version indicator of image to launch'),
    Ctrl('vol_base',     '--vol-base',     'DOCKER_VOL_BASE',        'volbase',     '/rw/dv/TMP',      '/rw/dv',          'base directory for relative bind-mount source points'),
]

class ControlsManager:
    def __init__(self, args, basedir, settings, test_mode, dev_mode):
        self.args, self.basedir, self.settings, self.dev_mode = args, basedir, settings, dev_mode
        self.test_mode = test_mode or dev_mode

    def resolve_control(self, control_name):
        try:
            ctrl = next(x for x in CONTROLS if x.control_name == control_name)
            return ctrl.resolve(self.args, self.basedir, self.settings, self.test_mode, self.dev_mode) if ctrl else None
        except StopIteration:
            raise Exception(f'internal error; no such control {control_name}')

CONTROLS_MANAGER = None  ## initialized by main()

def get_control(name): return CONTROLS_MANAGER.resolve_control(name)


# ----------------------------------------
# General purpose subroutines

def err(msg):
    sys.stderr.write("%s\n" % msg)
    return None


# ----------------------------------------
# 2nd level helpers

def expand_log_shorthand(log, name):
    ctrl = log.lower()
    if ctrl in ['n', 'none', 'z']:
        return ['--log-driver=none']
    elif ctrl == 's' or ctrl.startswith('s:') or ctrl.startswith('syslog'):
        if ':' in ctrl:
            ctrl, slog_addr = ctrl.split(':', 1)
        else:
            slog_addr = None
        args = ['--log-driver=syslog',
                '--log-opt', 'mode=non-blocking',
                '--log-opt', 'max-buffer-size=4m',
                '--log-opt', 'syslog-facility=local3',
                '--log-opt', 'tag={name}']
        if slog_addr: args.append(['--log-opt', f'syslog-address={slog_addr}'])
        return args
    elif ctrl in ['p', 'passthrough']:
        return []
    elif ctrl in ['j', 'journal', 'journald']:
        return ['--log-driver=journald']
    elif ctrl in ['j', 'json']:
        if 'podman' in get_control('docker_exec'): return ['--log-driver=json-file']
        return ['--log-driver=json-file',
                '--log-opt', 'max-size=5m',
                '--log-opt', 'max-file=3']
    else:
        if '--log-driver' in ctrl:
            return log.split(' ')
        else:
            return ['--log-driver'] + log.split(' ')


def add_devices(cmnd, dev_list):
    if not dev_list: return cmnd
    for i in dev_list:
        if '*' in i:
            globs = glob.glob(i)
            if not globs: err(f'WARNING: glob returned no items: {i}')
            for g in globs:
                cmnd.extend(['--device', g])
            continue
        else:
            cmnd.extend(['--device', i])
    return cmnd


def add_mounts(cmnd, mapper, readonly, name, mount_list):
    vol_base = get_control('vol_base')
    if not mount_list: return cmnd
    for i in mount_list:
        for src, dest in i.items():
            if '/' not in src:
                src = os.path.join(f'{vol_base}/{name}', src)
            if '*' in src:
                globs = glob.glob(src)
                if not globs: err(f'WARNING: glob returned no items: {src}')
                for g in globs:
                    cmnd = add_mounts_internal(cmnd, mapper, readonly, name, g, dest)
                continue
            if not os.path.exists(src):
                err(f'Creating non-existent mountpoint source: {src}')
                Path(src).mkdir(parents=True, exist_ok=True)
            cmnd = add_mounts_internal(cmnd, mapper, readonly, name, src, dest)
    return cmnd

def add_mounts_internal(cmnd, mapper, readonly, name, src, dest):
    if not dest: dest = src
    if mapper: src = mapper(src, name)
    ro = ',readonly' if readonly else ''
    cmnd.extend(['--mount', f'type=bind,source={src},destination={dest}{ro}'])
    return cmnd


def add_ports(cmnd, ports_list, test_mode_shift, enable_ipv6):
    for pair in ports_list:
        if not enable_ipv6 and not '.' in pair: pair = '0.0.0.0:' + pair
        if test_mode_shift:
            parts = pair.split(':')
            if len(parts) == 2:
                test_host_port = int(parts[0]) + test_mode_shift
                pair = f'{test_host_port}:{parts[1]}'
            elif len(parts) == 3:
                test_host_port = int(parts[1]) + test_mode_shift
                pair = f'{parts[0]}:{test_host_port}:{parts[2]}'
            else:
                raise Exception('unable to add test_mode_shift; cannot parse port pair: {pair}')
        cmnd.extend(['--publish', pair])
    return cmnd


def add_simple_control(cmnd, control_name, param=None):
    if param is None: param = '--' + control_name
    val = get_control(control_name)       # could be a list from json or a csv string from flags.
    if not val: return None

    if isinstance(val, str):
        if '.' in val: val_list = val.split(',')
        else: val_list = [val]
    for i in val_list:
        if param: cmnd.extend([param, i])
        else: cmnd.append(i)
        last_val = i
    return last_val


def clone_dir(src, dest):
    if os.path.exists(dest): return False
    if not os.path.exists(src):
        err(f'Creating non-existent mountpoint source: {src}')
        Path(src).mkdir(parents=True)
    Path(dest).mkdir(parents=True, exist_ok=True)
    stat = os.stat(src)
    os.chown(dest, stat.st_uid, stat.st_gid)
    os.chmod(dest, stat.st_mode)
    return True


def does_image_exist(repo_name, image_name, tag_name):
    if not repo_name: return False
    if ':' in repo_name: return True  # TODO(defer): any way to really test this?
    out = subprocess.check_output([get_control('docker_exec'), 'images', '-q', f'{repo_name}/{image_name}:{tag_name}'])
    return out != b''


def map_dir(destdir, name, include_tree=False, include_files=False):
    vol_base = get_control('vol_base')
    if '/' in destdir:
        mapped = '%s/%s/%s' % (vol_base, name, destdir.replace('/', '_'))
    else:
        mapped = destdir.replace(vol_base, vol_base)
    # Safety check (we're about to rm -rf from the mapped dir; make sure it's in the right place!)
    if 'TMP' not in mapped: raise Exception('Ouch- dir map failed: %s -> %s' % (destdir, mapped))
    # Make sure the mapped parent dir exists.
    clone_dir(os.path.dirname(destdir), os.path.dirname(mapped))
    # Destructive replace of the mapped dir.
    if os.path.exists(mapped):
        print('Removing previous alt dir: %s' % mapped)
        shutil.rmtree(mapped)
    # If not including the tree, the only thing to do is clone the top level dir.
    if not include_tree:
        if include_files: raise Exception('Error- cannot include files with including tree')
        clone_dir(destdir, mapped)
        return mapped
    # Copy over everything; trimming exsting files' contents if requested.
    if not os.path.isdir(destdir):
        # Nothing to copy, just create dest dir. (Ownership/perms might be wrong...)
        os.mkdir(mapped)
        return mapped
    cmd = ['/bin/cp', '-a' ]
    if not include_files: cmd.append('--attributes-only')
    cmd.extend([destdir, mapped])
    subprocess.check_call(cmd)
    # and remove the empty files if not needed.
    if not include_files: subprocess.check_call(['/usr/bin/find', mapped, '-type', 'f', '-size', '0b', '-delete'])
    return mapped

def map_to_empty_dir(destdir, name):  return map_dir(destdir, name, False, False)

def map_to_empty_tree(destdir, name): return map_dir(destdir, name, True, False)

def map_to_clone(destdir, name):      return map_dir(destdir, name, True, True)


def get_ip(hostname):
    try: return socket.gethostbyname(hostname)
    except Exception: return None


def get_ip_to_use():
    ip = get_control('ip')
    if ip in ['', '0']: return None
    if os.getuid() != 0: return err("skipping IP assignment; not running as root.")

    # If we don't see 3 dots, this must be a hostname we're intended to look up.
    if ip.count('.') != 3:
        lookup_host = ip if ip != '-' else get_control('hostname')
        ip = get_ip(lookup_host)
    return ip


def get_puid(name):
    '''Decorate the machine's PUID with a container-name specific one.'''
    system_puid = A.get_machine_private_data()
    return f'{system_puid}:{name}'


# Try to find the location of the specified docker container dir.
def search_for_dir(dir):
    if os.path.isdir(dir): return dir
    d_src_dir = os.environ.get('D_SRC_DIR')
    if d_src_dir and os.path.isdir(d_src_dir): return d_src_dir
    d_src_dir2 = os.environ.get('D_SRC_DIR2')
    if d_src_dir2 and os.path.isdir(d_src_dir2): return d_src_dir2
    cd = os.getcwd()
    if 'ktools/' in cd:
        pre, post = cd.split('ktools/', 1)
        candidate = '%s/ktools/containers/%s' % (pre, dir)
        if os.path.isdir(candidate): return candidate
    candidate = '%s/docker-dev/%s' % (os.environ.get('HOME'), dir)
    if os.path.isdir(candidate): return candidate
    return None    # Out of ideas...


# ----------------------------------------


def parse_settings(filename):
    if not os.path.isfile(filename): raise Exception(f'settings file not found: {filename} .  Either run from the docker dir to launch, or see --cd flag.')
    dirpath = os.path.dirname(os.path.abspath(filename))
    settings = {
        'settings_filename': filename,
        'settings_dir': dirpath,
        'settings_leaf_dir': dirpath.split('/')[-1]
    }
    with open(filename) as f:
        y = yaml.load(f, Loader=yaml.FullLoader)
    if y: settings.update(y)
    return settings


def gen_command():
    args = CONTROLS_MANAGER.args
    settings = CONTROLS_MANAGER.settings
    test_mode = CONTROLS_MANAGER.test_mode

    cmnd = [ get_control('docker_exec') ]

    name = add_simple_control(cmnd, 'name')
    basename = name.replace('test-', '')

    add_simple_control(cmnd, 'env')
    add_simple_control(cmnd, 'extra_docker', '')
    add_simple_control(cmnd, 'hostname')
    add_simple_control(cmnd, 'network')

    fg_control = get_control('foreground')
    fg = (fg_control == '1') or args.shell
    if not fg: cmnd.append('-d')

    cmnd.extend(expand_log_shorthand(get_control('log'), name))

    if get_control('rm') == '1': cmnd.append('--rm')

    if args.shell: cmnd.extend(['--user', '0', '-ti', '--entrypoint', '/bin/bash'])

    add_devices(cmnd, settings.get('mount_devices'))
    add_mounts(cmnd, None, True, basename, settings.get('mount_ro'))
    add_mounts(cmnd, None, False, basename, settings.get('mount_persistent'))
    add_mounts(cmnd, None, test_mode, basename, settings.get('mount_persistent_test_ro'))
    add_mounts(cmnd, map_to_empty_dir  if test_mode else None, False, basename, settings.get('mount_logs'))
    add_mounts(cmnd, map_to_empty_dir  if test_mode else None, False, basename, settings.get('mount_persistent_test_copy'))
    add_mounts(cmnd, map_to_empty_tree if test_mode else None, False, basename, settings.get('mount_persistent_test_copy_tree'))
    add_mounts(cmnd, map_to_clone      if test_mode else None, False, basename, settings.get('mount_persistent_test_copy_files'))
    if test_mode:
        add_mounts(cmnd, None, False, basename, settings.get('mount_test_only'))

    test_mode_shift = args.port_offset if test_mode else 0
    add_ports(cmnd, get_control('ports'), test_mode_shift, get_control('ipv6_ports') == 1)


    puid = get_control('puid')
    if puid == 'auto': puid = get_puid(basename)
    if puid: cmnd.extend(['--env', 'PUID=' + puid])

    image_name = get_control('image')
    tag_name = get_control('tag')

    repo_name = get_control('repo1')
    if not does_image_exist(repo_name, image_name, tag_name):
        repo_name = get_control('repo2')
        if not does_image_exist(repo_name, image_name, tag_name):
            repo_name = None
            err(f'This probably wont work; {image_name}:{tag_name} not found in primary or secondary repo.')

    if repo_name:
        full_spec = f'{repo_name}/{image_name}:{tag_name}'
    else:
        full_spec = f'{image_name}:{tag_name}'
    cmnd.append(full_spec)

    cmd = get_control('command')
    if cmd: cmnd.extend(cmd.split(' '))

    # Throw any additional init args on the end, if any are requested by flags or settings.
    extra_init = get_control('extra_init')
    if extra_init and not args.shell:
        cmnd.append('--')
        cmnd.extend(extra_init.strip().split(' '))

    return cmnd


# ----------------------------------------
# main

def parse_args(args=sys.argv[1:]):
    ap = argparse.ArgumentParser(description='docker container launcher')

    g1 = ap.add_argument_group('Modified run modes', 'Do something other than simply launching a container.')
    g1.add_argument('--debug',       '-d', action='store_true', help='Have each control value print out the source of its setting')
    g1.add_argument('--print-cmd',         action='store_true', help='Launch the container as normal, but also print out the command being used for the launch.')
    g1.add_argument('--test',        '-t', action='store_true', help='Just print the command that would be run rather than running it.')

    g2 = ap.add_argument_group('Meta settings', 'Flags that effect how all the other settings are set.')
    g2.add_argument('--cd',                default=None, help='Normally d-run is run from the docker directory of the container to launch.  If that is inconvenient, specify the name of the subdir of ~/docker-dev here, and we start by switching to that dir.')
    g2.add_argument('--port-offset', '-P', default=10000, help='add this value to host-side port mappings in --test-mode')
    g2.add_argument('--settings',    '-s', default='settings.yaml', help='location of the settings yaml file.  default of None will use "settings.yaml" in the current working dir.')
    g2.add_argument('--shell',       '-S', action='store_true', help='Override the entrypoint to an interactve tty-enable bash shell')
    g2.add_argument('--dev-mode',    '-D', action='store_true', help="Same as --test-mode, except change prefixes from 'test-' to 'dev-'")
    g2.add_argument('--test-mode',   '-T', action='store_true', help="Launch the container in test mode (changes most setting's defaults)")

    g3 = ap.add_argument_group('Individual launch params', 'These override settings and environment variable defaults')
    for c in CONTROLS:
        if not c.override_flag: continue
        g3.add_argument(c.override_flag, help=c.doc)

    return ap.parse_args(args)


def main():
    args = parse_args()

    global DEBUG
    if args.debug: DEBUG = True

    if args.cd:
        src_dir = search_for_dir(args.cd)
        if src_dir: os.chdir(src_dir)
        else: err(f'dont know how to find directory: {args.cd}')
    else:
        src_dir = os.getcwd()
    basedir = os.path.basename(src_dir)

    settings = parse_settings(args.settings)

    global CONTROLS_MANAGER
    CONTROLS_MANAGER = ControlsManager(args, basedir, settings, args.test_mode, args.dev_mode)

    cmnd = gen_command()

    if args.print_cmd or args.test:
        temp = ' '.join(map(lambda x: x.replace('--', '\t\\\n  --'), cmnd))
        last_space = temp.rfind(' ')
        print(temp[:last_space] + '\t\\\n ' + temp[last_space:])
        if args.test: sys.exit(0)

    return subprocess.call(cmnd)


if __name__ == "__main__":
    sys.exit(main())
