'''common settings for ktools, split up into selectable groups

common usage:

import kcore.kcore_settings as S
settings = S.init()
n = settings['name']

That's nice and terse, but "settings" is a local variable, probably in main().
To avoid you having to create your own global singleton, kcore_settings stores
one for you, so after calling init(), your code can reference settings without
a local, using various different options:

p =  S.s['puid']          # explicitly reference the singleton
hn = S.get('hostname')    # provided method implicitly uses the singleton

d = S.get_dict()          # or grab a dict for the most terse subsequent retrieval
n = d['name']


Note that the defaults of init() will implicitly attempt to load a global
settings file, which is specified in $KTOOLS_SETTINGS, but will default to
$HOME/.ktools/.settings if that variable isn't set.

'''

import os
import settings as S


# ----- module level state

s = None             # singleton built by init(), put here for easy reference by callers (so they don't need a singleton in their namespace)
TEST_MODE = False    # optionally set by init(), allows for mode-dependent defaults; see _mode() below.

KTOOLS_GLOBAL_SETTINGS = os.environ.get('KTOOLS_SETTINGS', '${HOME}/.ktools.settings')


# ---------- groupings of independently selectable Settings

GROUPS = [
    S.SettingsGroup('makefile', 'settings used by ktools Makefiles', S.Settings(add_Settings=[
        S.Setting('simple',      default='0',                                            doc='if not "0", use :install-simple rather than :install targets in Makefiles (e.g. see pylib/Makefile)'),
        S.Setting('root_ro',     default='0',                                            doc='if not "0", Makefiles will temporarily remount their target directorys\'s filesystems as +rw during :install.'),
    ])),

    S.SettingsGroup('pylib runtime', 'run-time controls for most of ktools/pylib', S.Settings(add_Settings=[
        S.Setting('keymaster_host',                                                      doc='{host}:{port} for the keymaster instance to use when retrieving keys'),
        S.Setting('varz_prom',   default='0',                                            doc='if not "0", varz will auto-generate Prometheus streams for all varz data.  Requires the Prometheus libraries be installed.'),
    ])),

    S.SettingsGroup('q', 'settings for q.py', S.Settings(add_Settings=[
        S.Setting('q_exclude',                                                           doc='list of ";" separated hosts to exclude from multi-host operations'),
        S.Setting('q_git_dirs',                                                          doc='list of ";" separated git directories to manage from "q"'),
        S.Setting('q_linux_hosts',                                                       doc='list of Linux hosts to manage from "q"'),
        S.Setting('q_pi_hosts',                                                          doc='list of Rpi hosts to manage from "q"'),
    ])),

    S.SettingsGroup('hc', 'settings for home-control', S.Settings(add_Settings=[
        S.Setting('hc_data',                                                             doc='directory where home_control system searches for its datafiles'),
    ])),

    S.SettingsGroup('containers', 'settings common to most container-related ktools', S.Settings(add_Settings=[
        S.Setting('docker_exec', default='/usr/bin/docker',                              doc='container manager to use (docker or podman)'),
        S.Setting('d_src_dir',                                                           doc='first directory to look in when searching for the source directory for containers to build/launch/whatever'),
        S.Setting('d_src_dir2',                                                          doc='second directory to look in when searching for the source directory for containers to build/launch/whatever'),
        S.Setting('repo1',                                                               doc='when building, destination repo to save image to.  when launching, first repo to try for a matching image'),
        S.Setting('repo2',                                                               doc='second repo to try for a matching image'),
        S.Setting('shift-gids',                                                          doc='user_ns mapping shift for group ids inside the container.  Used when auto-creating volume directories with specified ownerships.'),
        S.Setting('shift-uids',                                                          doc='user_ns mapping shift for user ids inside the container.  Used when auto-creating volume directories with specified ownerships.'),
    ])),

    S.SettingsGroup('container launching', 'settings common to selecting containers to launch', S.Settings(add_Settings=[
        S.Setting('image',       default='@basedir',                                     doc='name of the image to build/launch'),
        S.Setting('tag',         default=lambda: _mode('live', 'latest'),                doc='tagged or other version indicator of image to build or launch', flag_aliases=['-t']),
    ])),

    S.SettingsGroup('autostart', 'setting for which auto-start wave to use for a container', S.Settings(add_Settings=[
        S.Setting('autostart',   flag_name=None,                                         doc='string indicating startup wave to auto-launch this container system system boot.  Used by d.py, not d-run.py'),
    ])),

    S.SettingsGroup('container building', 'settings for building containers', S.Settings(add_Settings=[
        S.Setting('build_params',                                                        doc='a list of ";" separated params to send to the "${DOCKER_EXEC} build" command when building images'),
    ])),

    S.SettingsGroup('d', 'settings for d.py', S.Settings(add_Settings=[
        S.Setting('cmd',                                                                 doc='use this as the command to run as init in the container, rather than whatever is listed in the Dockerfile'),
        S.Setting('dns',         default='$KTOOLS_DRUN_DNS', default_env_value='',       doc='IP address of DNS server inside container'),
        S.Setting('env',                                                                 doc='list of ";" separated name=value pairs to add to the container\'s environment'),
        S.Setting('extra_docker',default='$KTOOLS_DRUN_EXTRA', default_env_value='',     doc='list of additional command line arguments to send to the container launch CLI'),
        S.Setting('extra_init',                                                          doc='list of additional arguments to pass to the init command within the container'),
        S.Setting('fg',          default=lambda: _mode('0', '1'), value_type=bool,       doc='if flag set or setting is "1", run the container in foreground with interactive/pty settings'),
        S.Setting('hostname',    default=lambda: _mode('@basedir', 'test-@basedir'),     doc='host name to assign within the container'),
        S.Setting('ip',          default=lambda: _mode('\-', '0'),                       doc='IP address to assign container.  Use "-" for dns lookup of container\'s hostname.  Use "0" (or dns failure) for auto assignment'),
        S.Setting('ipv6_ports',  default='0', value_type=bool,                           doc='if flag set or setting is "1", enable IPv6 port mappings.'),
        S.Setting('log',         default=lambda: _mode('none', 'passthrough'),           doc='log driver for stdout/stderr from the container.  p/passthrough, j/journald, J/json, s/syslog[:url], n/none'),
        S.Setting('mount-ro',                                                            doc='list of ";" separated src:dest pairs to mount read-only inside the container'),
        S.Setting('mount-rw',                                                            doc='list of ";" separated src:dest pairs to mount read+write inside the container'),
        S.Setting('name',        default=lambda: _mode('@basedir', 'test-@basedir'),     doc='name to assign to the container (for container management)'),
        S.Setting('network',                                                             doc='container network to use'),
        S.Setting('ports',                                                               doc='list of ";" separated {host}:{container} ports to map'),
        S.Setting('puid',        default='auto',                                         doc='if not "auto", pass the given value into $PUID inside the container.  "auto" will generate a consistent container-specific value.  Blank to disable.'),
        S.Setting('rm',          default='1', value_type=bool,                           doc='if flags set or setting is "1" (the default), set the container to remove its leftovers once it stops'),
        S.Setting('tz',          default='\-',                                           doc='timezone to set inside the container (via $TZ).  Default of "-" will look for /etc/timezone'),
        S.Setting('vol-owner',                                                           doc='owner to use (if not otherwise specified) for any files or directories created by [vols]'),
        S.Setting('vol-perms',                                                           doc='permissions to use (if not otherwise specified) for any files or directories created by [vols]'),
        S.Setting('vol-base',                                                            doc='base directory for relative bind-mount source points'),
        S.Setting('vols',                                                                doc='list of ";" separated directories (relative to [vol-base]) to create, if necessary, before launching'),
    ]))
]


# ---------- API

def init(selected_groups, argparse_instance=None, files_to_load=[], debug=False, test_mode=None):
    global s, TEST_MODE
    if test_mode is not None: TEST_MODE = test_mode

    if KTOOLS_GLOBAL_SETTINGS and os.path.isfile(KTOOLS_GLOBAL_SETTINGS) and KTOOLS_GLOBAL_SETTINGS not in files_to_load:
        files_to_load.insert(0, KTOOLS_GLOBAL_SETTINGS)

    s = S.Settings(files_to_load, flag_prefix='', debug=debug)
    s.add_settings_groups(GROUPS, selected_groups)
    if argparse_instance: settings.add_flags_in_groups(arpparse_instance, GROUPS, selected_groups)
    return s


# convenience methods for callers

def get(name): return s.get(name)
def get_dict(): return s.get_dict()


# ---------- internal helpers

def _mode(production_value, test_mode_value):
    return test_mode_value if TEST_MODE else production_value
