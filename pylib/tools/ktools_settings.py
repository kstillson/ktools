#!/usr/bin/python3

'''common settings for ktools, split up into selectable groups

common usage:

import kcore.ktools_settings as S
settings = S.init()
n = settings['name']

That's nice and terse, but "settings" is a local variable, probably in main().
To avoid you having to create your own global singleton, ktools_settings stores
one for you, so after calling init(), your code can reference settings without
a local, using various different options:

p =  S.s['puid']          # explicitly reference the singleton
hn = S.get('hostname')    # provided method implicitly uses the singleton

d = S.get_dict()          # or grab a dict for the most terse subsequent retrieval
n = d['name']

Note: the defaults of init() will implicitly attempt to load a global settings
file, which is specified in $KTOOLS_SETTINGS, but will default to
$HOME/.ktools_settings if that isn't set.

'''

import os, sys
import kcore.settings as S


# ----- constants for external reference

STR_LIST_SEP = ';'


# ----- module level state

s = None             # singleton built by init(), put here for easy reference by callers (so they don't need a singleton in their namespace)
TEST_MODE = False    # optionally set by init(), allows for mode-dependent defaults; see _mode() below.

KTOOLS_GLOBAL_SETTINGS = os.environ.get('KTOOLS_SETTINGS', os.path.expanduser('~/.ktools.settings'))


# ---------- groupings of independently selectable Settings

GROUPS = [
    S.SettingsGroup('makefile', 'settings used by ktools Makefiles', S.Settings(add_Settings=[
        S.Setting('simple',      default='0',                                            doc='if not "0", use :install-simple rather than :install targets in Makefiles (e.g. see pylib/Makefile)'),
        S.Setting('root_ro',     default='0',                                            doc='if not "0", Makefiles will temporarily remount their target directorys\'s filesystems as +rw during :install.'),
    ])),

    S.SettingsGroup('pylib runtime', 'run-time controls for most of ktools/pylib', S.Settings(add_Settings=[
        S.Setting('keymaster_host',                                                      doc='{host}:{port} for the keymaster instance to use when retrieving keys'),

        # Note: the setting to control varz Prometheus has been left in the env variable $KTOOLS_VARZ_PROM
        # (because varz.py and webserver_base.py are lower-level than the ../tools/ktools_settings.py system)
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
        S.Setting('shift_gids',                                                          doc='user_ns mapping shift for group ids inside the container.  Used when auto-creating volume directories with specified ownerships.'),
        S.Setting('shift_uids',                                                          doc='user_ns mapping shift for user ids inside the container.  Used when auto-creating volume directories with specified ownerships.'),
    ])),

    S.SettingsGroup('container launching', 'settings common to selecting containers to launch', S.Settings(add_Settings=[
        S.Setting('image',       default='%{_settings_basedir}',                         doc='name of the image to build/launch'),
        S.Setting('tag',         default=lambda: _mode('live', 'latest'),                doc='tagged or other version indicator of image to build or launch'),
    ])),

    S.SettingsGroup('autostart', 'setting for which auto-start wave to use for a container', S.Settings(add_Settings=[
        S.Setting('autostart',   flag_name=None,                                         doc='string indicating startup wave to auto-launch this container system system boot.  Used by d.py, not d-run.py'),
    ])),

    S.SettingsGroup('container building', 'settings for building containers', S.Settings(add_Settings=[
        S.Setting('build_params',                                                        doc='a list of ";" separated params to send to the "[docker_exec] build" command when building images'),
        S.Setting('build_push_opts', default='--tls-verify=false',                       doc='extra params to use when pushing a build to a repo'),
        S.Setting('build_push_to',   default='localhost:5000',                           doc='default repo to push to'),
    ])),

    S.SettingsGroup('d-run', 'settings for d-run.py', S.Settings(add_Settings=[
        S.Setting('cmd',                                                                 doc='use this as the command to run as init in the container, rather than whatever is listed in the Dockerfile'),
        S.Setting('dns',                                                                 doc='IP address of DNS server inside container'),
        S.Setting('env',                                                                 doc='list of ";" separated name=value pairs to add to the container\'s environment'),
        S.Setting('extra_docker',                                                        doc='list of additional command line arguments to send to the container launch CLI'),
        S.Setting('extra_init',                                                          doc='list of additional arguments to pass to the init command within the container'),
        S.Setting('fg',          default=lambda: _mode('0', '1'), flag_type=bool,        doc='if flag set or setting is "1", run the container in foreground with interactive/pty settings'),
        S.Setting('hostname',    default='%{name}',                                      doc='host name to assign within the container'),
        S.Setting('ip',          default=lambda: _mode(r'\-', '0'),                      doc='IP address to assign container.  Use "-" for dns lookup of container\'s hostname.  Use "0" (or dns failure) for auto assignment'),
        S.Setting('ipv6_ports',  default='0', flag_type=bool,                            doc='if flag set or setting is "1", enable IPv6 port mappings.'),
        S.Setting('log',         default='none',                                         doc='log driver for stdout/stderr from the container.  p/passthrough, j/journald, J/json, s/syslog[:url], n/none'),
        S.Setting('mount_ro',                                                            doc='list of ";" separated src:dest pairs to mount read-only inside the container'),
        S.Setting('mount_rw',                                                            doc='list of ";" separated src:dest pairs to mount read+write inside the container'),
        S.Setting('name',                                                                doc='name to assign to the container (for container management)',
                  default=lambda: _mode('%{_settings_basedir}', 'test-%{_settings_basedir}'),
                  default_env_value='?'),    # in-case something like settings.get_dict() is called, but we haven't successfully loaded a settings file yet.
        S.Setting('no_rm',       default='0', flag_type=bool,                            doc='do not autoremove container remanants upon termination'),
        S.Setting('network',                                                             doc='container network to use'),
        S.Setting('ports',                                                               doc='list of ";" separated {host}:{container} ports to map'),
        S.Setting('port_offset', default=lambda: _mode('0', '10000'),                    doc='shift host port assignments up by this much (mostly used for testing mode to avoid the production containers ports'),
        S.Setting('puid',        default='auto',                                         doc='if not "auto", pass the given value into $PUID inside the container.  "auto" will generate a consistent container-specific value.  Blank to disable.'),
        S.Setting('rm',          default='1', flag_type=bool,                            doc='if flags set or setting is "1" (the default), set the container to remove its leftovers once it stops'),
        S.Setting('shell',       default='0', flag_type=bool,                            doc='if flag set or setting is "1", override the container entrypoing and present an interactive shell instead'),
        S.Setting('tz',          default=r'\-',                                          doc='timezone to set inside the container (via $TZ).  Default of "-" will look for /etc/timezone'),
        S.Setting('vol_owner',                                                           doc='owner to use (if not otherwise specified) for any files or directories created by [vols]'),
        S.Setting('vol_perms',                                                           doc='permissions to use (if not otherwise specified) for any files or directories created by [vols]'),
        S.Setting('vol_base',                                                            doc='base directory for relative bind-mount source points'),
        S.Setting('vols',                                                                doc='list of ";" separated directories (relative to [vol_base]) to create, if necessary, before launching'),
    ]))
]


# ---------- API

def init(selected_groups=None, files_to_load=[], argparse_instance=None,
         flag_aliases={}, global_settings_filename=KTOOLS_GLOBAL_SETTINGS,
         debug=False, test_mode=None):
    global s, TEST_MODE

    # If called by implicit/lazy call to get, we might still need to be able to parse global settings...
    if not files_to_load: files_to_load = os.environ.get('KTOOLS_SETTINGS', '${HOME}/.ktools.settings')

    # other param fix-ups
    if isinstance(files_to_load, str): files_to_load = [files_to_load]
    if selected_groups is None: selected_groups = [i.name for i in GROUPS]
    if test_mode is not None: TEST_MODE = test_mode

    # Enable flags (with no prefix) and environment variable sources (KT_ and KTO_ prefixes) for everything..
    for group in GROUPS:
        group.settings.reset_cached_values()   # (testing sometimes reuses the singleton)
        group.settings.flag_prefix = ''
        group.settings.tweak_all_settings('env_name', 'KT_{name}')
        group.settings.tweak_all_settings('override_env_name', 'KTO_{name}')

    s = S.Settings(files_to_load, flag_prefix='', debug=debug)
    s.add_settings_groups(GROUPS, selected_groups)

    if flag_aliases: add_flag_aliases(s, flag_aliases)
    if argparse_instance: s.add_flags_in_groups(argparse_instance, GROUPS, selected_groups)
    return s


def add_flag_aliases(settings_instance, dict_name_to_alias):
    for name, addl_alias in dict_name_to_alias.items():
        setting = settings_instance.get_setting(name)
        if not setting: raise ValueError(f'Alias provided for unknown setting: {name}')
        if isinstance(addl_alias, list): setting.flag_aliases.extend(addl_alias)
        else:                            setting.flag_aliases.append(addl_alias)


# convenience methods for callers
# includes lazy call to init() if needed (loads just the default and global settings)

def get(name):
    if not s: init()
    return s.get(name)

def get_bool(name):
    if not s: init()
    return s.get_bool(name)

def get_dict():
    if not s: init()
    return s.get_dict()


# ---------- internal helpers

def _mode(production_value, test_mode_value):
    return test_mode_value if TEST_MODE else production_value


# ---------- main (for printing setting values)

def main(argv=[]):
    ap = S.parse_main_args(None)
    args, _ = ap.parse_known_args(argv or sys.argv[1:])
    settings = init(selected_groups=None,
                    files_to_load=[args.host_settings, args.settings],
                    argparse_instance=ap, debug=args.debug)
    S.print_selected_settings(settings, '*' if args.all else args.settings_list, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
