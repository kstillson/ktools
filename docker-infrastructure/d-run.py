#!/usr/bin/python3

'''
TODO(doc)

Supported features in the settings file:

debug_alt_cmnd: string
extra_init: string
debug_extra_init: string
env: list of env assignment strings
extra_docker: string
foreground: 1   (note: ignored when --vol-alt, which requires background launches)
hostname: string
image: name of image to run
ip: string {'-' for dns-based, '' to let docker assign}
log: string{N|J|S|custom spec}
name: string (flag overrides this, this overrides directory name)
network: string{NONE|name of network to use.}
port: list of ports to forward: host:container

mount option                       normal behavior                   -v behavior
------------                       ---------------                   -----------
mount_logs                         list of bind-mount maps s->d      create empty +w dir in alt location
mount_persistent                   "                                 same as normal (caution: can affect real data)
mount_persistent_test_copy         "                                 same as mount_logs, top level dir only
mount_persistent_test_copy_tree    "                                 clone src dir struct in alt location; no files
mount_persistent_test_copy_files   "                                 recursive copy src to alt location
mount_persistent_test_ro           "                                 mount real location, but ro
mount_ro                           list of ro bind-mount maps s->d   same as normal
mount_test_only                    ignored                           list of bind-mount maps s->d
   relative paths are relative to  $DOCKER_VOL_BASE/{name}/...       $DOCKER_VOL_BASE/TMP/{name}/...

Most settings can come from multiple sources, the priority order is:
  command-line flag, then settings file, then environment variable, then hard-coded "fallback" value.

'''

import argparse, glob, os, shutil, socket, subprocess, sys, yaml
from pathlib import Path

import kcore.auth

# ---------- control constants

DOCKER_EXEC =      os.environ.get('DOCKER_EXEC',               '/usr/bin/docker')
HOSTNAME_ENV =     os.environ.get('KTOOLS_DRUN_HOSTNAME',      None)      # None => use container name
IP_ENV =           os.environ.get('KTOOLS_DRUN_IP',            '-')
LOG_ENV =          os.environ.get('KTOOLS_DRUN_LOG',           'journald')
NAME_ENV =         os.environ.get('KTOOLS_DRUN_NAME',          None)      # None => use container name
NETWORK_ENV =      os.environ.get('KTOOLS_DRUN_NETWORK',       'bridge')
REPO_ENV =         os.environ.get('KTOOLS_DRUN_REPO',          'ktools')
REPO2_ENV =        os.environ.get('KTOOLS_DRUN_REPO2',         None)
TAG_ENV =          os.environ.get('KTOOLS_DRUN_TAG',           'live')
TEST_NETWORK_ENV = os.environ.get('KTOOLS_DRUN_TEST_NETWORK',  'bridge')
VOL_BASE =         os.environ.get('DOCKER_VOL_BASE',           '/rw/dv')


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
        return ['--log-driver=passthrough'] if 'podman' in DOCKER_EXEC else []
    elif ctrl in ['j', 'json', 'journal', 'journald']:
        if 'podman' in DOCKER_EXEC: return ['--log-driver=journald']
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
    if not mount_list: return cmnd
    for i in mount_list:
        for src, dest in i.items():
            if '/' not in src:
                src = os.path.join(f'{VOL_BASE}/{name}', src)
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


def add_ports(cmnd, ports_list, enable_ipv6):
    for pair in ports_list:
        if not enable_ipv6 and not '.' in pair: pair = '0.0.0.0:' + pair
        cmnd.extend(['--publish', pair])
    return cmnd


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
    out = subprocess.check_output([DOCKER_EXEC, 'images', '-q', f'{repo_name}/{image_name}:{tag_name}'])
    return out != b''


def map_dir(destdir, name, include_tree=False, include_files=False):
    if '/' in destdir:
        mapped = '%s/TMP/%s/%s' % (VOL_BASE, name, destdir.replace('/', '_'))
    else:
        mapped = destdir.replace(VOL_BASE, VOL_BASE + '/TMP')
    # Safety check (we're about to rm -rf from the mapped dir; make sure it's in the right place!)
    if 'TMP' not in mapped: sys.exit('Ouch- dir map failed: %s -> %s' % (destdir, mapped))
    # Make sure the mapped parent dir exists.
    clone_dir(os.path.dirname(destdir), os.path.dirname(mapped))
    # Destructive replace of the mapped dir.
    if os.path.exists(mapped):
        print('Removing previous alt dir: %s' % mapped)
        shutil.rmtree(mapped)
    # If not including the tree, the only thing to do is clone the top level dir.
    if not include_tree:
        if include_files: sys.exit('Error- cannot include files with including tree')
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


def get_ip_to_use(args, settings):
    ip = args.ip or settings.get('ip', None) or IP_ENV
    if ip in ['', '0']: return None
    if os.getuid() != 0: return err("skipping IP assignment; not running as root.")

    # If we don't see 3 dots, this must be a hostname we're intended to look up.
    if ip.count('.') != 3:
        lookup_host1 = ip if ip != '-' else settings['hostname']
        ip = get_ip(lookup_host1)
        if not ip:
            lookup_host2 = settings['basename']
            ip = get_ip(lookup_host2)
        if not ip and args.name_prefix:
            lookup_host3 = lookup_host2.replace(args.name_prefix, '')
            ip = get_ip(lookup_host3)
            if not ip:
                err(f'unable to find ip for hostname (tried {lookup_host1}/{lookup_host2}/{lookup_host3}); will let Docker pick IP.')
                ip = None
    if args.subnet:
        if not ip or ip.count('.') != 3:
            err('unable to process --subnet flag; IP is being selected by docker.')
        else:
            orig_ip = ip
            temp = ip.split('.')
            temp[2] = args.subnet
            ip = '.'.join(temp)
            if orig_ip != ip: print(f'subnet setting changed IP from {orig_ip} to {ip}')
    return ip


def get_puid(name):
    '''Decorate the machine's PUID with a container-name specific one.'''
    system_puid = kcore.auth.get_machine_private_data()
    return f'{system_puid}:{name}'


# Try to find the location of the specified docker container dir.
def search_for_dir(dir):
    if os.path.isdir(dir): return dir
    cd = os.getcwd()
    if 'ktools/' in cd:
        pre, post = cd.split('ktools/', 1)
        candidate = '%s/ktools/docker-containers/%s' % (pre, dir)
        if os.path.isdir(candidate): return candidate
    candidate = '%s/docker-dev/%s' % (os.environ.get('HOME'), dir)
    if os.path.isdir(candidate): return candidate
    return None    # Out of ideas...


# ----------------------------------------

def parse_args():
    ap = argparse.ArgumentParser(description='docker container launcher')

    # Flags that help d-run select which container to launch.
    ap.add_argument('--cd',           default=None, help='Normally d-run is run from the docker directory of the container to launch.  If that is inconvenient, specify the name of the subdir of ~/docker-dev here, and we start by switching to that dir.')
    ap.add_argument('--image',  '-i', default=None, help='Name of image to use; default of None will use container name.')
    ap.add_argument('--latest', '-l', action='store_true', help='Shorthand for --tag=latest')
    ap.add_argument('--repo',         default=REPO_ENV, help=f'repo prefix for image name.  default="{REPO_ENV}"')
    ap.add_argument('--repo2',        default=None, help=f'backup repo prefix to try if image:tag does not exist in --repo.  Default="{REPO2_ENV}"')
    ap.add_argument('--tag',    '-T', default=None, help=f'tag or hash of image version to use.  Default is "{TAG_ENV}".')

    # Flags that provide context about the mode we're launching the container in.
    ap.add_argument('--dev',           '-D',  action='store_true', help='Activate development mode (equiv to: --fg --name_prefix=dev- --network=docker2 --rm --subnet=3 --latest --vol-alt).')
    ap.add_argument('--dev-test',      '-DT', action='store_true', help='Same as --dev but use --name_prefix=test-')
    ap.add_argument('--settings',      '-s',  default=None, help='location of the settings yaml file.  default of None will use "settings.yaml" in the current working dir.')
    ap.add_argument('--test-in-place', '-P',  action='store_true', help='Run dev version in real container (equiv to: --fg --rm --latest).')

    # Flags that override or are merged with individual settings to fine-tune individual flags passed to the container launch.
    ap.add_argument('--cmd',            default=None, help='Specify the inside-container command or args to run.')
    ap.add_argument('--extra-docker',   default=None, help='Any additional flags to pass to the docker command.')
    ap.add_argument('--extra-init',     default=None, help='Any additional flags to pass the the init command.')
    ap.add_argument('--env',      '-e', default=[], nargs='*', help='Any additional environment variables to set in the container')
    ap.add_argument('--fg',             action='store_true', help='Run the container in the foreground')
    ap.add_argument('--hostname', '-H', default=None, help=f'use a particular hostname.  Default is "{HOSTNAME_ENV}".  Blank/none will use the contain name. Supports replacement of string HOSTNAME with the hosts name .')
    ap.add_argument('--ip',             default=None, help=f'assign a particular IP address.  Default is {IP_ENV}.  Use "-" to look up hostname in dns and use returned value.  Use "" (or dns lookup failure) to let docker pick.')
    ap.add_argument('--log',      '-L', default=None, help=f'Log driver to use.  Allowed: p/passthrough, n/none, s/syslog[:url] (e.g. s:udp://sysloghost:514), j/json, or any other value to pass blindly on to Docker.  Default value is "{LOG_ENV}".')
    ap.add_argument('--name',     '-n', default=None, help=f'use a specified container name.  Default of None will use the name of the directory that contains the settings file')
    ap.add_argument('--network',  '-N', default=None, help=f'Name of docker network to use.  Default is "{NETWORK_ENV}"')
    ap.add_argument('--ports',    '-p', default=None, nargs='*', help='Port to map, host:container (can specify flag multiple times')
    ap.add_argument('--rm',             action='store_true', help='Ask docker to auto-remove the container when it stops.')
    ap.add_argument('--puid',           default='auto', help='Use give value for $PUID rather than auto-generating.  Remember you probably want this to be container-specific.  Set blank to skip assignment.  See kcore/auth.py for details.')
    ap.add_argument('--subnet',         default=None, help='If specified, use existing logic to determine IP number, but then map that number to this subnet.')
    ap.add_argument('--ipv6',     '-6', action='store_true', help='If not specified, make port bindings specific to IPv4 only.')

    # Flags that tweak the way d-run works.
    ap.add_argument('--fail-on-exists',     action='store_true', help='fail if a container with this name already exists.  default will auto-remove the conflicting container instance (which only works if its shut down).')
    ap.add_argument('--name_prefix',        default='', help='If specified, use normal logic to determine the container name, but prefix it with this string.')
    ap.add_argument('--print-cmd',          action='store_true', help='Print launch command before executing it.')
    ap.add_argument('--vol-alt',      '-v', action='store_true', help='Mount non-read-only volumes in alternate locations.  Also send send debug_extra_init settings.  This is a subset of --dev, and --dev is probably what you want.')

    # Flags that activate an entirely different mode of operation from the usual.
    ap.add_argument('--shell',   '-S', action='store_true', help='If activated, override the normal entrypoint and use foreground interactive tty-enabled bash.')
    ap.add_argument('--test',    '-t', action='store_true', help='Just print the command that would be run rather than running it.')

    args = ap.parse_args()
    if args.latest: args.tag = 'latest'
    if args.test_in_place:
        args.fg = True
        args.rm = True
        ##@@ if not args.log: args.log = 'NONE'
        if not args.tag: args.tag = 'latest'
    elif args.dev or args.dev_test:
        args.fg = True
        ##@@ if not args.log: args.log = 'NONE'
        if not args.name_prefix: args.name_prefix = 'test-' if args.dev_test else 'dev-'
        if not args.network: args.network = TEST_NETWORK_ENV
        args.rm = True
        if not args.subnet: args.subnet = '3'
        if not args.tag: args.tag = 'latest'
        args.vol_alt = True

    return args


def parse_settings(args):
    filename = args.settings if args.settings else './settings.yaml'
    if not os.path.isfile(filename): sys.exit('settings file not found: %s .  Either run from the docker dir to launch, or see --cd flag.' % filename)
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


def gen_command(args, settings):
    cmnd = [DOCKER_EXEC, 'run']
    fg = (args.fg
          or args.shell
          or (settings.get('foreground',0) == 1  and not args.vol_alt))
    if not fg: cmnd.append('-d')
    settings['basename'] = basename = settings['settings_leaf_dir']
    name = settings['name'] = (args.name_prefix or '') + (args.name or NAME_ENV or settings['basename'])
    cmnd.extend(['--name', name])

    hostname = args.hostname or settings.get('hostname') or HOSTNAME_ENV or name
    hostname = hostname.replace('HOSTNAME', socket.gethostname())
    settings['hostname'] = hostname
    cmnd.extend(['--hostname', hostname])

    network = args.network or settings.get('network', None) or NETWORK_ENV
    if network != 'NONE':
        cmnd.extend(['--network', network])
        ip = get_ip_to_use(args, settings)
        if ip: cmnd.extend(['--ip', ip])
    else:
        cmnd.extend(['--network', 'none'])

    add_env = settings.get('env') or []
    add_env.extend(args.env)
    for i in add_env: cmnd.extend(['--env', i])

    if args.log:
        cmnd.extend(expand_log_shorthand(args.log, name))
    elif settings.get('log'):
        cmnd.extend(expand_log_shorthand(settings['log'], name))
    else:
        cmnd.extend(expand_log_shorthand('S', name))

    if args.extra_docker: cmnd.extend(args.extra_docker.split(' '))
    if settings.get('extra_docker'): cmnd.extend(settings['extra_docker'].split(' '))
    if args.rm: cmnd.append('--rm')

    if args.shell:
        cmnd.extend(['--user', '0', '-ti', '--entrypoint', '/bin/bash'])
    else:
        if settings.get('debug_alt_cmnd') and args.vol_alt:
            cmnd.extend(['--entrypoint', settings['debug_alt_cmnd']])

    add_devices(cmnd, settings.get('mount_devices'))
    add_mounts(cmnd, None, True, basename, settings.get('mount_ro'))
    add_mounts(cmnd, None, False, basename, settings.get('mount_persistent'))
    add_mounts(cmnd, None, args.vol_alt, basename, settings.get('mount_persistent_test_ro'))
    add_mounts(cmnd, map_to_empty_dir  if args.vol_alt else None, False, basename, settings.get('mount_logs'))
    add_mounts(cmnd, map_to_empty_dir  if args.vol_alt else None, False, basename, settings.get('mount_persistent_test_copy'))
    add_mounts(cmnd, map_to_empty_tree if args.vol_alt else None, False, basename, settings.get('mount_persistent_test_copy_tree'))
    add_mounts(cmnd, map_to_clone      if args.vol_alt else None, False, basename, settings.get('mount_persistent_test_copy_files'))
    if args.vol_alt:
        add_mounts(cmnd, None, False, basename, settings.get('mount_test_only'))

    tag_name = args.tag or TAG_ENV

    if 'ports' in settings:
        if args.dev or args.dev_test:
            print('skipping settings port mapping because in dev mode.')
        elif tag_name != 'live':
            print('skipping settings port mapping because tag != "live"')
        else:
            add_ports(cmnd, settings.get('ports'), args.ipv6)
    if args.ports: add_ports(cmnd, args.ports, args.ipv6)

    if args.puid:
        cmnd.extend(['--env', 'PUID=%s' % (args.puid if args.puid != 'auto' else get_puid(name))])

    if 'image' in settings:
        image = settings.get('image')
    else:
        repo_name = args.repo
        image_name = args.image or basename
        if not does_image_exist(repo_name, image_name, tag_name):
            repo_name = args.repo2 or REPO2_ENV
            if not does_image_exist(repo_name, image_name, tag_name):
                err(f'This probably wont work; {image_name}:{tag_name} does not exist in either {args.repo} or {args.repo2}')
        image = f'{repo_name}/{image_name}:{tag_name}'
    cmnd.append(image)
    if args.cmd: cmnd.extend(args.cmd.split(' '))

    # Throw any additional init args on the end, if any are requested by flags or settings.
    if not args.shell:
      extra_init = args.extra_init or ''
      # If in alt mode, allow debug_extra_init to override extra_init if provided, use plain extra_init if debug_extra_init not provided.
      if args.vol_alt:
          if settings.get('debug_extra_init'):
              extra_init += ' ' + settings['debug_extra_init']
          else:
              if settings.get('extra_init'): extra_init += ' ' + settings['extra_init']
      else:
          if settings.get('extra_init'): extra_init += ' ' + settings['extra_init']
      if extra_init: cmnd.extend(extra_init.strip().split(' '))

    return cmnd


# ----------------------------------------
# main

def main():
    args = parse_args()
    if args.cd:
        dir = search_for_dir(args.cd)
        if dir: os.chdir(dir)
        else: err(f'dont know how to find directory: {dir}')
    settings = parse_settings(args)
    cmnd = gen_command(args, settings)
    if args.print_cmd or args.test:
        temp = ' '.join(map(lambda x: x.replace('--', '\t\\\n  --'), cmnd))
        last_space = temp.rfind(' ')
        print(temp[:last_space] + '\t\\\n ' + temp[last_space:])
        if args.test: sys.exit(0)
    if not args.fail_on_exists:
        with open('/dev/null', 'w') as z:
            subprocess.call([DOCKER_EXEC, 'rm', settings['name']], stdout=z, stderr=z)
    return subprocess.call(cmnd)


if __name__ == "__main__":
  sys.exit(main())
