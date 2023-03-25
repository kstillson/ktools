#!/usr/bin/python3

'''Launch a container.

This scripts constructs the command-line parameters for Docker to launch a
container. '''

import glob, grp, os, pprint, pwd, shutil, socket, subprocess, sys
from dataclasses import dataclass

import kcore.auth as A
import kcore.common as C
import kcore.settings as KS
import ktools.ktools_settings as S


# ---------- global controls

DEBUG = False
TEST_MODE = False


# ---------- general purpose helpers

def Debug(msg):
    if DEBUG: err('DEBUG: ' + msg)


def err(msg):
    sys.stderr.write("%s\n" % msg)
    return False


def get_setting(name, skip_auto_test_mode=False):
    if TEST_MODE and not skip_auto_test_mode:
        test_val = S.get('test_' + name)
        if test_val is not None: return test_val
    return S.get(name)


def get_bool_setting(name):
    return KS.eval_bool(get_setting(name))


# ---------- internal business logic helpers

def expand_log_shorthand(log, name):
    ctrl = log.lower()
    if ctrl == '-':
        return []
    elif ctrl in ['n', 'none', 'z']:
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
                '--log-opt', f'tag={name}']
        if slog_addr: args.extend(['--log-opt', f'syslog-address={slog_addr}'])
        return args
    elif ctrl in ['p', 'passthrough']:
        return []
    elif ctrl in ['j', 'journal', 'journald']:
        return ['--log-driver=journald']
    elif ctrl in ['j', 'json']:
        if 'podman' in get_setting('docker_exec'): return ['--log-driver=json-file']
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


def add_mounts(cmnd, container_name, control_name, read_only):
    '''Appends mount params to cmnd, also returns a set of the vol_base-relative source directories
       so these can be used as implicit volume directories (to be created if needed).'''
    vol_dir_srcs = set()
    vol_base = get_setting('vol_base')
    if not vol_base: raise ValueError('setting "vol_base" not defined and no sensible default available.')
    mounts = get_setting(control_name)
    if not mounts: return vol_dir_srcs
    for i in mounts:
        if isinstance(i, str):
            k, v = i.split(',', 1)
            i = {}
            i[k.strip()] = v.strip()
        for src, dest in i.items():
            if not src.startswith('/'):
                src = os.path.join(vol_base, container_name, src)
                vol_dir_srcs.add(src)
            ro = ',readonly' if read_only else ''
            cmnd.extend(['--mount', f'type=bind,source={src},destination={dest}{ro}'])
    return vol_dir_srcs


def add_ports(cmnd, ports_list, test_mode_shift, enable_ipv6):
    if not ports_list: return cmnd
    for pair in ports_list:
        if isinstance(pair, dict):
            first_key = next(iter(pair))
            pair = f'{first_key}:{pair[first_key]}'
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
    val = get_setting(control_name)       # could be a list from json or a csv string from flags.
    if val is None: return None

    last_val = None
    val_list = val if isinstance(val, list) else val.split(S.STR_LIST_SEP)
    for i in val_list:
        if not i: continue
        if param: cmnd.extend([param, i])
        else: cmnd.append(i)
        last_val = i
    return last_val


def does_image_exist(repo_name, image_name, tag_name):
    if not repo_name: return False
    if ':' in repo_name: return True  # TODO(defer): any way to really test this?
    out = subprocess.check_output([get_setting('docker_exec'), 'images', '-q', f'{repo_name}/{image_name}:{tag_name}'])
    return out != b''


def get_ip(hostname):
    try: return socket.gethostbyname(hostname)
    except Exception: return None


def get_ip_to_use():
    ip = get_setting('ip')
    if ip in ['', '0']: return None
    if os.getuid() != 0: return err("skipping IP assignment; not running as root.")

    # If we don't see 3 dots, this must be a hostname we're intended to look up.
    if ip.count('.') != 3:
        lookup_host = ip if ip != '-' else get_setting('hostname')
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
    if d_src_dir:
        candidate = os.path.join(d_src_dir, dir)
        if os.path.isdir(candidate): return candidate
    d_src_dir2 = os.environ.get('D_SRC_DIR2')
    if d_src_dir2:
        candidate = os.path.join(d_src_dir2, dir)
        if os.path.isdir(candidate): return candidate
    cd = os.getcwd()
    if 'ktools/' in cd:
        pre, post = cd.split('ktools/', 1)
        candidate = os.path.join(pre, 'ktools/containers',  dir)
        if os.path.isdir(candidate): return candidate
    candidate = os.path.join(os.environ.get('HOME'), 'docker-dev', dir)
    if os.path.isdir(candidate): return candidate
    return None    # Out of ideas...


# ---------- creating mounted-volume directories (and sometimes files)

@dataclass
class VolSpec:
    path:      str = None    # remember not to prefix with "/" if relative to vol_base
    item_type: str = 'dir'   # can be specified as "type:" in a serialized VolSpec dict.
    owner:     str = None    # can be a uid (as a string), a username, or "user/{container uid}"
    group:     str = None    # can be a gid (as a string), a group-name, or "group/{container gid}"
    perm:      str = None    # expect a base 8 number in string form, e.g. "0750"
    contents:  str = None    # only useful if item_type=='file'

    def depth(self): return self.path.count('/')


def assemble_vol_specs(mount_src_dirs, base_name):
    specs = []               # output list of VolSpec's
    paths = set()            # list of processed paths to avoid duplicates

    # Get defaults for unspecified details.
    vol_base = get_setting('vol_base')
    vol_defaults = get_setting('vol_defaults') or {}
    default_owner = _resolve_inside_container_owner(vol_defaults.get('owner'))
    default_group = _resolve_inside_container_group(vol_defaults.get('group'))
    default_perm = vol_defaults.get('perm')

    if not vol_base: raise ValueError('Need to specify setting vol_base, probably in the global settings file.')

    # Entries are either strings (which give the path to create), or dicts,
    # which can selectively override default parameters.  In the dict case,
    # there should be one item with no value- that key becomes the string that
    # specifies the volume path name.  This looks odd data-structure-wise,
    # but looks nice and intuitative in the yaml.
    vols = get_setting('vols') or []
    for vol in vols:
        if isinstance(vol, str):
            path = vol if vol.startswith('/') else os.path.join(vol_base, base_name, vol)
            spec = VolSpec(path, 'dir', default_owner, default_group, default_perm, None)

        elif isinstance(vol, dict):
            spec = VolSpec('?', 'dir', default_owner, default_group, default_perm, None)
            for k, v in vol.items():
                if k == 'type': k = 'item_type'   # "type" is a reserved Python word, so internally we use item_type to avoid an illegal field name in VolSpec.
                if v is None or v == 'path':
                    spec.path = k if k.startswith('/') else os.path.join(vol_base, base_name, k)
                    continue
                if k == 'contents': spec.item_type = 'file'
                if hasattr(spec, k): setattr(spec, k, v)
                else: err(f'ignoring unknown param "{k}" with value "{v}" for volume "{spec}"')
            if spec.path == '?': raise ValueError(f'Unknown path for volspec: {vol}')

        else: raise ValueError('Do not know how to process volspec: {vol}')

        spec.owner = _resolve_inside_container_owner(spec.owner)
        spec.group = _resolve_inside_container_group(spec.group)
        specs.append(spec)
        paths.add(spec.path)

    # Add in any remaining implicit vols from the mount source points
    for i in mount_src_dirs:
        if i in paths: continue          # ignore items we've already got queued
        Debug(f'adding implicit volspec for dir {i}')
        specs.append(VolSpec(i, 'dir', default_owner, default_group, default_perm, None))

    return specs


def _resolve_inside_container_owner(owner):
    if not owner: return owner
    if not owner.startswith('user/'): return owner
    user = owner.replace('user/', '')
    uid = None
    with open('files/etc/passwd') as f:
        for line in f:
            if line.startswith(f'{user}:'):
                parts = line.split(':')
                uid = int(parts[2])
                if 'podman' in get_setting('docker_exec'):
                    owner = str(uid)
                else:
                    shift = int(get_setting('shift_uids') or '0')
                    owner = str(uid + shift)
                break
    if uid is None:
        try:
            owner = str(pwd.getpwnam(user).pw_uid)
        except KeyError:
            err(f'unable to find files/etc/passwd entry for {owner} to chown {path}.  Will try just chowning to {user}')
            owner = user
    return owner


def _resolve_inside_container_group(group):
    if not group: return group
    if not group.startswith('group/'): return group
    group_name = group.replace('group/', '')
    gid = None
    with open('files/etc/group') as f:
        for line in f:
            if line.startswith(f'{group_name}:'):
                parts = line.split(':')
                gid = int(parts[2])
                if 'podman' in get_setting('docker_exec'):
                    group = str(gid)
                else:
                    shift = int(get_setting('shift_gids') or '0')
                    group = str(gid + shift)
                break
    if gid is None:
        try:
            group = str(grp.getgrnam(group_name).gr_gid)
        except KeyError:
            err(f'unable to find files/etc/group entry for {group} to chown {path}.  Will try just chowning to {group}')
            group = group_name
    return group


def create_vol_dirs(mount_src_dirs, base_name, test_mode):
    vol_specs = assemble_vol_specs(mount_src_dirs, base_name)
    if DEBUG: Debug(f'volume dirs to check/create:\n{pprint.pformat(vol_specs)}')

    # Remove any previous auto-created test items.  Order such that children go
    # before parents, so we don't attempt double deletes.
    if test_mode and (get_setting('vol_base', skip_auto_test_mode=True) !=
                      get_setting('test_vol_base', skip_auto_test_mode=True)):
        for volspec in sorted(vol_specs, key=lambda x: -x.depth()):
            delete_vol_item(volspec)

    # Order such that parents created before children.  The creation logic
    # actually contains a check to make sure parents exist, but that causes
    # the parent to inherit the child's owner/group/perm settings.  If the
    # user specified different settings for the parent, we want to use those,
    # so create the parent first to give its settings priority.
    for volspec in sorted(vol_specs, key=lambda x: x.depth()):
        create_vol_item(volspec)


def create_vol_item(volspec):
    mode = int(volspec.perm, 8) if volspec.perm else None

    # Note: we don't check the ownership or perms of existing directories or
    # files; this script could easily get very complicated or not-as-smart-as-
    # it-thinks-it-is.  If something's already there, assume it's right.
    if os.path.exists(volspec.path):
        return Debug(f'{volspec.path} already exists')

    # Create our parent directory if it's not already there.
    parent = os.path.dirname(volspec.path)
    if not os.path.isdir(parent):
        Debug(f'making recursive call to create missing parent: {parent}')
        create_vol_item(VolSpec(parent, 'dir', volspec.owner, volspec.group, volspec.perm))

    # Create the requested item.
    if volspec.item_type == 'file':
        with open(volspec.path, 'w') as f: f.write(_vol_eval_contents(volspec))
        if mode: os.chmod(volspec.path, mode)

    elif volspec.item_type == 'dir':
        os.mkdir(volspec.path)
        if mode: os.chmod(volspec.path, mode)

    else: raise(f'internal error; unknown vtype "{volspec.item_type}" for {volspec.path}')

    fix_ownership(volspec)
    return Debug(f'created {str(volspec)}')


def _vol_eval_contents(volspec):
    val = volspec.contents
    if not val: return ''
    val = val.replace('%target%',    volspec.path)
    val = val.replace('%targetdir%', os.path.dirname(volspec.path))
    val = val.replace('%owner%',     volspec.owner)
    val = val.replace('%group%',     volspec.group)

    if   val.startswith('file:'):    val = C.read_file(val.replace('file:', ''))
    elif val.startswith('cmd:'):     val = _vol_popen_contents(val, volspec.path)
    elif val.startswith('command:'): val = _vol_popen_contents(val, volspec.path)
    elif val.startswith('popen:'):   val = _vol_popen_contents(val, volspec.path)
    return val


def _vol_popen_contents(val, target_path):
    _, cmd = val.split(':', 1)
    newval = C.popener(cmd, shell=True)
    if DEBUG: Debug(f'Generated volume contents for file "{target_path}" via command "{cmd}" -> "{newval}"')
    return newval


def delete_vol_item(volspec):
    path = volspec.path
    # TODO(defer): remove once we're confident in this; fails if test_vol_base doesn't contain 'TEST'.
    if not 'TEST' in path: raise ValueError(f'attempt to delete non TEST volspec item: {path=}')
    if volspec.item_type == 'dir' and os.path.isdir(path):
        err('!! Removing previous test dir: %s' % path)
        shutil.rmtree(path)
    elif volspec.item_type == 'file' and os.path.isfile(path):
        err('!! Removing previous test file: %s' % path)
        os.unlink(path)


def fix_ownership(volspec):
    '''If using podman, we might not be root, so utilize the "unshare" option to
       perform the chown inside the userns mapping.  This means we do not want
       to shift the uid's: the userns will do that for us.  For Docker, there
       is no unshare option, so we've got to be root and use traditional
       chown.  But for this case, we do need to manually shift the target uid.'''
    if not volspec.path: return

    path = volspec.path   # local copies to allow modification
    owner = str(volspec.owner or '')
    group = str(volspec.group or '')
    docker_exec = get_setting('docker_exec')

    if 'podman' in docker_exec:
        Debug(f'  podman chown {path} -> {owner}')
        if owner:
            rslt = C.popen([docker_exec, 'unshare', 'chown', owner, path])
            if not rslt.ok: return err(f'error: attempt to podman/unshare chown {path} to {owner} failed: {rslt.out}')
        if group:
            rslt = C.popen([docker_exec, 'unshare', 'chgrp', group, path])
            if not rslt.ok: return err(f'error: attempt to podman/unshare chgrp {path} to {group} failed: {rslt.out}')

    elif os.getuid() == 0:
        Debug(f'  root chown {path} -> {owner}.{group}')
        if owner:
            rslt = C.popen(['chown', owner, path])
            if not rslt.ok: return err(f'error: attempt to chown {path} to {owner} failed: {rslt.out}')
        if group:
            rslt = C.popen(['chgrp', group, path])
            if not rslt.ok: return err(f'error: attempt to chgrp {path} to {group} failed: {rslt.out}')

    else:
        return Debug(f'Skipping chown to {owner} for {path} because not root and not using podman.')


# ---------- primary business logic: construct the launch command

def gen_command():
    cmnd = [ get_setting('docker_exec'), 'run' ]

    name = add_simple_control(cmnd, 'name')
    basename = name.replace('test-', '')

    add_simple_control(cmnd, 'dns')
    add_simple_control(cmnd, 'env')
    add_simple_control(cmnd, 'extra_docker', '')
    add_simple_control(cmnd, 'hostname')
    add_simple_control(cmnd, 'network')

    if get_setting('network') != 'none':
        ip = get_ip_to_use()
        if ip: cmnd.extend(['--ip', ip])

    if not (get_bool_setting('fg') or get_bool_setting('shell')): cmnd.append('-d')

    cmnd.extend(expand_log_shorthand(get_setting('log'), name))

    tz = get_setting('tz')  # timezone
    if tz == '-': tz = C.read_file('/etc/timezone').strip()
    if tz: cmnd.extend(['--env', f'TZ={tz}'])

    if get_bool_setting('rm'): cmnd.append('--rm')

    if get_bool_setting('shell'): cmnd.extend(['--user', '0', '-ti', '--entrypoint', '/bin/bash'])

    add_devices(cmnd, get_setting('mount_devices'))

    mount_src_dirs =      add_mounts(cmnd, basename, 'mount_ro', True)
    mount_src_dirs.update(add_mounts(cmnd, basename, 'mount_rw', False))

    create_vol_dirs(mount_src_dirs, basename, TEST_MODE)

    add_ports(cmnd, get_setting('ports'), S.s.get_int('port_offset'), get_bool_setting('ipv6_ports'))

    puid = get_setting('puid')
    if puid == 'auto': puid = get_puid(name)
    if puid: cmnd.extend(['--env', 'PUID=' + puid])

    image_name = get_setting('image')
    tag_name = get_setting('tag')

    repo_name = get_setting('repo1')
    if not does_image_exist(repo_name, image_name, tag_name):
        repo_name = get_setting('repo2')
        if not does_image_exist(repo_name, image_name, tag_name):
            repo_name = None
            err(f'This probably wont work; {image_name}:{tag_name} not found in primary or secondary repo.')

    if repo_name: full_spec = f'{repo_name}/{image_name}:{tag_name}'
    else:         full_spec = f'{image_name}:{tag_name}'
    cmnd.append(full_spec)

    cmd = get_setting('cmd')
    if cmd: cmnd.extend(cmd.split(' '))

    # Add any additional init args on the end.
    extra_init = get_setting('extra_init')
    if extra_init and not get_bool_setting('shell'):
        if isinstance(extra_init, list): cmnd.extend(extra_init)
        else: cmnd.extend(extra_init.strip().split(' '))

    return cmnd


# ---------- args & settings

def try_dirs(dirlist):
    for dir in dirlist:
        if os.path.isdir(dir): return dir


def parse_args(argv=sys.argv[1:]):
    ap = C.argparse_epilog(description='docker container launcher', add_help=False)  # Defer help until after we've added our settings-based flags.

    g1 = ap.add_argument_group('d-run logic options', 'Do something other than simply launching a container.')
    g1.add_argument('--debug',         '-d', action='store_true', help='Print the source of each control value, and final command as a list (showing args are separate)')
    g1.add_argument('--help',          '-h', action='store_true', help='print help')
    g1.add_argument('--print-cmd',           action='store_true', help='Launch the container as normal, but also print out the command being used for the launch.')
    g1.add_argument('--test',          '-t', action='store_true', help='Just print the command that would be run rather than running it.')

    g2 = ap.add_argument_group('Meta settings', 'Flags that effect how all the other settings are set.')
    g2.add_argument('--cd',            '-N', help='The directory within which to find --settings (if not specified in --settings).  Can be relative to the global setting "d_src_dir" or "d_src_dir2", meaning that this can just be the basename of the container you want to launch (hence the alias -N for name)')
    g2.add_argument('--settings',      '-s', default='settings.yaml', help='file with container specific settings')
    g2.add_argument('--host_level_settings', '-H', default='${HOME}/.kcore.settings', help='file with host-level overall settings')
    g2.add_argument('--test-mode',     '-T', action='store_true', help='Launch with alternate settings, so version under test does not interfere with production version.')

    g3 = ap.add_argument_group('shortcuts')
    g3.add_argument('--latest',        '-l', action='store_true', help='shortcute for --tag=latest')

    args, _ = ap.parse_known_args(argv)   # Parse enough flags to get the settings dir & filename(s)

    # Now we have the initially known args, so we can initialize the settings
    # system and let it fully populate our flags.

    flag_aliases = {
        'repo1': '-r',
        'image': '-i',
        'cmd':   '-c',
        'shell': '-S',
    }
    s = S.init(['containers', 'container launching', 'd-run'],
               C.special_arg_resolver(args.host_level_settings),
               ap, flag_aliases, args.debug, args.test_mode)

    # Add environment varaible fallbacks for all settings.
    s.tweak_all_settings('env_name', 'DRUN_{name}')

    # Now that our flags are populated, we can go ahead and fully parse those.
    args = ap.parse_args(argv)            # parse for real this time.
    s.set_args(args)

    # Now we know d_src_dir[2], so we can locate and load the container-specific settings file.
    if args.cd:
        found_dir = try_dirs([args.cd,
                              os.path.join(s['d_src_dir'], args.cd),
                              os.path.join(s['d_src_dir2'], args.cd)])
        if found_dir: os.chdir(found_dir)
        else: err(f'warning- unable to find directory for --cd: {args.cd}')

    settings_filename = os.path.abspath(args.settings)
    basedir = os.path.basename(os.path.dirname(settings_filename))
    s.set_replacement_map({'@basedir': basedir, 'test-@basedir': 'test-' + basedir})

    try:
        s.parse_settings_file(args.settings)
    except ValueError:
        err('\n\nUnable to find settings file to launch.  Try --cd or --settings flags.\n\n')
        print(ap.format_help())
        sys.exit(1)


    # ----- Okay, args and settings are fully loaded, there are a few simple ones we can handle locally.

    # Handle help
    if args.help:
        print(ap.format_help())
        sys.exit(0)

    # Handle shortcuts
    if args.latest:
        args.tag = 'latest'
        s.tweak_setting('tag', 'cached_value', 'latest')

    # Handle simple global toggles
    global DEBUG, TEST_MODE
    DEBUG = args.debug
    TEST_MODE = args.test_mode

    return args    # No need to return s, that's available via the module ktools_settings singleton "s"


# ---------- main

def main():
    args = parse_args()

    # generate the launch command and output any requested debugging info.
    cmnd = gen_command()

    if DEBUG or args.print_cmd or args.test:
        # err(f'@@ {cmnd}')  # Used to seek out param separation problems...
        temp = ' '.join(map(lambda x: x.replace('--', '\t\\\n  --'), cmnd))
        last_space = temp.rfind(' ')
        err(temp[:last_space] + '\t\\\n ' + temp[last_space:])
        if args.test: sys.exit(0)

    # clear out any terminated-but-still-laying-around remanents of previous runs.
    if not S.s['no_rm']:
        with open('/dev/null', 'w') as z:
            subprocess.call([get_setting('docker_exec'), 'rm', get_setting('name')], stdout=z, stderr=z)

    # actually run the launch command
    return subprocess.call(cmnd)


if __name__ == "__main__":
    sys.exit(main())
