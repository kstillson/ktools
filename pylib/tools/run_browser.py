#!/usr/bin/python3

'''Security-focused browser selector / launcher.

This script can launch Chrome or Firefox (much better tested w/ Chrome) in a
number of different configurations, that add various layers of security for
browsing.

Firstly, the script can launch browsers as different Linux user id's.  For
this to work, this script must be able to relaunch itself under sudo as
whatever browser uids are desired, and those uid's must be registered with the
xhost command as allowed to launch programs in the original user's X-windows.
The idea here is that you can run browsers as (various) special purpose uid's
that have access to nothing else on the system, so the impact of those uid's
being infested with malware is reduced.  The script also knows how to launch
browsers with various different "profiles," although it should be noted this
is much more a user-convenience than a serious security protection.

By default, when an alternate uid is used, the script assumes the only thing
this uid is being used for is browsing, so when the browser exits, it will
search for processes still running as that uid.  Under normal circumstances
there shouldn't be any, so it offers to kill them.  If you don't want this,
use --purge=no.

Secondly, the script can add various additional sandbox protections around
browsers.  The primary mode is "firejail," which adds a layer of system call
filters that make it harder for an infected browser to interact with
components outside the browser or to persist the malware beyond the current
session.

In addition, the script can launch a browser that talks to another browser
running inside KASM- a container hosting service generally run on a (possibly
remote) VM.

Thirdly, the script has a concept of restting-to-last-saved-snapshot.  This
basically wipes out the profile-specific portion of a browser's configuration
upon each launch, and sets it back to a known-good snapshot.  You can update a
browser configuration's snapshot either when it's running or after it's exited
(but before re-starting it!).  In this way, you can persist only the changes
you want and specifically make a snapshot, and otherwise, you keep returning
to the previously known state.  i.e., if malware manages to infiltrate your
browser, it should get wiped out on the next browser restart.  This 'reset'
works for both local and KASM-based instances (using rsync to talk to KASM
server, which requires you to set up appropriate ~/.ssh/authorized_keys
file(s)).

When using a KASM-based configuration, the "appmode" setting controls the
local browser's launch mode.  In "normal mode", (appmode=None), it just runs
the browser as usual.  You'll have to manually login to KASM and select the
remote browser to execute.  You'll also have to be careful when typing things
like control-w, as that will close the local browser window, not the remote.
With appmode="-", a local Chrome browser is launched in application-mode,
which gets rid of local hotkeys, bookmarks, etc, meaning that those keystrokes
will be interpreted by the fully-featured remote browser (probably what you
want).  If appmode is set to the name of a KASM "cast" configuration, then the
local browser will automatically start that configuration, which essentially
selects the KASM-app to launch (e.g. selecting the remote browser for you).

The script also supports a simple user-id mutual exclusion mode.
Specifically, a configuration can list a set of usernames (or glob-style
username patterns) that are not allowed to be running when that config is
launched.  This allows you to make sure that particularly critical
configurations are mutually exclusive with particularly untrusted
configurations (assuming the latter is running in alternate uid's)

The fields "sync_acct", "pw_db", and "note" are just their to help you
identify browser configurations; they have no effect on the script's
operation.

Browser configurations are specified by arbitrary names (usually code letters
that are meaningful to you), and support aliases so you can give any number of
names to a config.  A --debug and --dryrun modes are supplied, so you can
experiment with options and make sure you understand what the script
is/would-be doing.

TODO(defer): break-out config section into separate file to make easier
for users to make site-specific changes w/o affecting git controlled file.

'''

import fnmatch, os, psutil, signal, sys, tempfile, time
from collections import namedtuple
from enum import Enum

import kcore.common as C


ARGS = None  # populated by main()

# Fields sync_acct and after are for information only; they don't effect the launch.
Cfg = namedtuple('browser_config', 'uid browser sandbox reset profile args appmode dis_uids sync_acct pw_db note aliases')

B =  Enum('Browsers', 'CHROME FIREFOX')
Sb = Enum('Sandbox',  'FIREJAIL KASM FIREKASM SNAP')  # FIREKASM => fj on local browser, and remote kasm browser

CURRENT_USER = os.environ.get('USER') or os.environ['USERNAME']


# ---------- site specific

BACKUP_SFX =      os.environ.get('B_BACKUP_SUFFIX', '.prev')  # set to None to disable backuping up the previous snapshot.
SNAPSHOT_DIR    = os.environ.get('B_SNAPSHOT_DIR',  os.path.expanduser('~/ktools/Bsnaps'))
DBUS =            os.environ.get('B_DBUS',         'auto')   # True/False/'auto'. 'auto' will launch a dbus session whenever a selected browser uid is different from the one that runs the launch command.
FIREJAIL_PREFIX = os.environ.get('B_FIREJAIL',     ['/usr/bin/firejail', '--whitelist=~/.pulse', '--whitelist=/root/dev/private-containers/stable-diffusion-webui-docker/data', '--'])
KASM_PERSIST =    os.environ.get('B_KASM_PERSIST', 'kasm:/home/persist/{kasm_workspace}/{kasm_login}/.config/{browser}/{kasm_browser_profile}')  # use ~/.ssh/config to change remote user/port
KASM_URL =        os.environ.get('B_KASM_URL',     'https://home.point0.net:4445')

# ---- browser launch configs

ARGS0 = []
ARGS1 = ['--window-size=2000,1200', '--window-position=200,100"']   # Note: Chrome supports these; ffx doesn't (but does a better job or remembering last window pos)

# When sandbox=Sb.{KASM|FIREKASM}, reset should be a string "kasm:{kasm_workspace}:{kasm_login}:{kasm_browser_profile}"
KASM1 = 'kasm:chrome-b:ken-b:Default'
KASM2 = 'kasm:chrome-bbb:ken-bbb:Default'

CONFIGS = { #   uid        browser      sandbox      reset          profile     args    appmode dis-uids    sync_acct        pw_db             note                                             aliases
    # Standard Chrome browsing w/o kasm
    'bf':   Cfg('ken-bf',  B.CHROME,    None,        True,          'Default',  ARGS1,  None,   ['ken-*'],  None,            'lp:ken@p0',      '[AC-4] Financial browser direct(fj)',          []),

    # Standard Firefox browsing w/o kasm
    'k':     Cfg('ken',    B.CHROME,    Sb.FIREJAIL, True,          'Default',    ARGS1,  None,   None,       None,          'lp:kstillson@g', '[AC-c] Chrome Google:* direct(fj)',            ['g','google','kstillson']),
    'knj':   Cfg('ken',    B.CHROME,    None,        True,          'Default',    ARGS1,  None,   None,       None,          'lp:kstillson@g', '[AC-c] Chrome Google:* direct(no fj)',         []),

    'b':    Cfg('ken-b',   B.FIREFOX,   Sb.FIREJAIL, True,          'Default',    ARGS0,  None,   None,       None,          'lp:ken@kds',     'Firefox general browsing direct(fj)',          []),
    'bnj':  Cfg('ken-b',   B.FIREFOX,   None,        True,          'Default',    ARGS0,  None,   None,       None,          'lp:ken@kds',     'Firefox general browsing direct(no fj)',       []),

    'bbb':  Cfg('ken-bbb', B.FIREFOX,   Sb.FIREJAIL, True,          'Default',    ARGS0,  None,   None,       None,          'ff-internal',    'Bad boy Firefox(fj)',                          []),
    'bbbnj':Cfg('ken-bbb', B.FIREFOX,   None,        True,          'Default',    ARGS0,  None,   None,       None,          'ff-internal',    'Bad boy Firefox(no fj)',                       []),

    # firefox separate space for proton extension integration
    'p':    Cfg('ken-b',   B.FIREFOX,   Sb.FIREJAIL, True,          'proton',     ARGS0,  None,   None,       None,          'protonpass',     'Firefox general browsing direct(fj)',          []),

    # Experimental / other
    'e':    Cfg('ken',     B.FIREFOX,   None,        False, 'add-on experiments', ARGS0, None,   None,       None,           None,            'Firefox for add-on dev/experiments',            ['addon', 'exp']),

    # Raw browser access (no added security)
    'R':    Cfg('ken',     B.CHROME,    None,        False,         None,       ARGS1,  None,   None,       'ks@g',          'lp:ks@g',       'raw chrome',                                    ['raw']),
    'F':    Cfg('ken',     B.FIREFOX,   None,        False,         None,       ARGS0,  None,   None,       None,            None,            'raw firefox',                                   ['f', 'ff']),

    # Browsing w/ kasm
     #'kb':   Cfg('ken-b',   B.CHROME,    Sb.FIREKASM,     KASM1,         'kasm-b',   ARGS1,  'b',    None,       'chrome-b@p0',   'lp:ken@kds',     '[SC-c] General browsing (kasm/foxyproxy)',      []),
     #'kbbb': Cfg('ken-bbb', B.CHROME,    Sb.FIREKASM,     KASM2,         'kasm-bbb', ARGS1,  'bbb',  None,       'chrome-bbb@p0', 'pm:chrome-bbb',  '[AC-b] Bad boy (kasm/foxyproxy, app mode)',     ['b3']),
     # # Specialized modes (mostly for debugging frozen kasms)
     #'kb1':  Cfg('ken-b',   B.CHROME,    Sb.FIREKASM,     KASM1,         'kasm-b',   ARGS1,  '-',    None,       'chrome-b@p0',   'lp:ken@kds',     'General browsing (kasm/foxyproxy w/o cast',     []),
     #'kb2':  Cfg('ken-b',   B.CHROME,    Sb.FIREKASM,     KASM1,         'kasm-b',   ARGS1,  None,   None,       'chrome-b@p0',   'lp:ken@kds',     'General browsing (kasm/foxyproxy, no app mode)',[]),

    # Deprecated modes
     #'b0':   Cfg('ken-b',   B.CHROME,    Sb.FIREJAIL, True,          'Default',  ARGS1,  None,   None,       'chrome-b@p0',   'lp:ken@kds',     '[AC-0] General browsing direct(fj)',           []),
     #'kk':   Cfg('ken',     B.FIREFOX,   Sb.FIREJAIL, True,          'kenp0',    ARGS0,  None,   None,       None,           None,             '(unused alt profile) ffox Google:ken@p0 direct(fj)',                 []),
     #'bbb0': Cfg('ken-bbb', B.CHROME,    Sb.FIREJAIL, True,          'Default',  ARGS1,  None,   None,       'chrome-bbb@p0', 'pm:chrome-bbb',  '[AC-9] Bad boy direct(fj)',                     ['b30']),
     #'ctrl': Cfg('ken',     B.CHROME,    Sb.FIREJAIL, True,    'control accts',  ARGS1,  None,   None,       'ken@p0',        'lp:kstillson@g', 'Google control accounts',                       ['C']),
     #'kff':  Cfg('ken',     B.FIREFOX,   Sb.FIREJAIL, True,        'kstillson',  ARGS0,  None,   None,       None,          'lp:kstillson@g', 'ffox Google:* direct(fj); issues w/ drive',    []),
     #'m':    Cfg('ken-b',   B.FIREFOX,   Sb.FIREJAIL, True,       'media-control', ARGS0,  None,   None,       None,          None,             'Firefox media control',                        []),

}


# ---------- helpers

def debug(msg):
    if ARGS.debug: print(f'DEBUG: {msg}', file=sys.stderr)


def quick_ok(msg): C.zinfo(msg, timeout=0.7)


# ---------- business logic

def check_disallowed_uids(cfg, bypass):
    if ARGS.sudo_done: return   # Always done pre-sudo (else might incorrect tag ourselves).
    if not cfg.dis_uids: return
    if bypass: return quick_ok('disallowed uid check bypassed')

    active_users = set()
    for proc in psutil.process_iter(['username']): active_users.add(proc.info['username'])

    for forbidden in cfg.dis_uids:
        for user in active_users:
            if fnmatch.fnmatch(user, forbidden):
                fatal(f'cannot launch with uid {user} running processes')
    debug('disallowed uids check ok')


def cleanup():
    '''Kill all pids running as current uid, except for myself.'''

    if not ARGS.sudo_done: return
    purge_request = ARGS.purge[0].lower()  # y/n/a
    if purge_request == 'n': return
    uid_to_purge = os.geteuid()
    debug(f'searching for leftover processes runing as {uid_to_purge}')
    time.sleep(0.5)
    pids = []
    prompt = 'Kill these processes?\n\n'
    for proc in procs_as_uid(uid_to_purge):
        pids.append(proc.pid)
        txt = f'  pid={proc.pid}  uid={proc.uids()[1]}  {proc.name()}'
        debug(f'found: {txt}')
        prompt += txt + '\n'
    if not pids: return
    debug(f'Found these pids: {pids}')
    if purge_request == 'a':
        ok = C.popen(['zenity', '--title', f'Leftover processes running as uid {uid_to_purge}', '--question', '--text', prompt])
        if not ok.ok: return debug('pid purge aborted by user request')
    elif purge_request != 'y':
        return warning(f'unknown value passed to --purge: {ARGS.purge} should be yes/no/ask.  pid purge skipped.', background=False)
    if ARGS.dryrun:
        return print(f'DRYRUN: would kill {pids}', file=sys.stderr)
    for pid in pids:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
    time.sleep(0.5)
    still_there = procs_as_uid(uid_to_purge)
    debug(f'processes that survived the purge: {still_there}')
    if still_there:
        return C.zwarn(f'{len(still_there)} of {len(pids)} resisted the purge')
    debug(f'{len(pids)} processes purged')


def procs_as_uid(uid, skip_names=['zenity'], skip_self=True):
    pid_to_skip = os.getpid() if skip_self else -1
    procs = []
    for proc in psutil.process_iter(['pid', 'ppid', 'name', 'uids']):
        if proc.uids()[1] != uid: continue
        if proc.pid == pid_to_skip: continue
        if proc.name() in skip_names: continue
        procs.append(proc)
    return procs


def find_chrome_profile_dir(name):
    if not name: return None
    basedir = os.path.expanduser('~/.config/google-chrome')
    state = C.read_file(os.path.join(basedir, 'Local State'))
    #old fmt: profile = C.popener(['jq', '-r', '.profile.info_cache | to_entries | .[] | select(.value.name == env.srch) | .key'], stdin_str=state, env={'srch': name})
    profile = C.popener(['jq', '-r', '.profile.info_cache | to_entries | .[] | select(.key == env.srch) | .value.name'], stdin_str=state, env={'srch': name})
    debug(f'profile label "{name}" returned profile dir: {profile}')
    if not profile: return None
    return os.path.join(basedir, profile.replace('"', ''))


def find_firefox_profile_dir(name):
    basedir = os.path.expanduser('~/snap/firefox/common/.mozilla/firefox')
    if not os.path.isdir(basedir): basedir = os.path.expanduser('~/.mozilla/firefox')
    import configparser
    c = configparser.ConfigParser()
    c.read(os.path.join(basedir, 'profiles.ini'))
    for i,v in c.items():
        if name:
            if v.get('Name') == name: return os.path.join(basedir, v['Path'])
        else:
            if v.get('Default') == '1': return os.path.join(basedir, v['Path'])
    return None


def get_kasm_profile_dir(cfg):
    return subst(KASM_PERSIST, cfg)


def get_profile_dir(cfg):
    if cfg.browser == B.CHROME: return find_chrome_profile_dir(cfg.profile)
    elif cfg.browser == B.FIREFOX: return find_firefox_profile_dir(cfg.profile)
    else: return None


def get_snapshot_dir(cfg):
    browser = 'chrome-' if cfg.browser == B.CHROME else 'firefox-' if cfg.browser == B.FIREFOX else 'qq-'
    prefix = 'kasm-' if cfg.sandbox in [Sb.KASM, Sb.FIREKASM] else ''
    return safedir(subst(os.path.join(SNAPSHOT_DIR, browser + prefix + cfg.uid, cfg.profile or 'Default'), cfg))


def launch(cfg):
    os.chdir(os.path.expanduser('~'))

    # ---- prep & setup environ

    dbus = DBUS
    if dbus == 'auto':
        if cfg.sandbox == Sb.SNAP: dbus = False
        else:                      dbus = ARGS.sudo_done
        debug(f'dbus auto resolved to: {dbus}')

    if cfg.uid and cfg.uid != CURRENT_USER:
        os.environ['PULSE_SERVER'] = 'unix:/tmp/pulse-server'
    else:
        os.environ['PULSE_SERVER'] = 'tcp:127.0.0.1:4713'
    debug(f'$PULSE_SERVER set to {os.environ["PULSE_SERVER"]}')

    # ---- construct command to run

    cmd = []
    if dbus: cmd.append('dbus-run-session')
    if cfg.sandbox in [Sb.FIREJAIL, Sb.FIREKASM]:
        cmd.extend(FIREJAIL_PREFIX)

    if   cfg.browser == B.CHROME:  cmd.append('google-chrome')
    elif cfg.browser == B.FIREFOX: cmd.append('firefox')
    else: fatal(f'unknown browser specified: {cfg.browser}')

    if cfg.profile:
        if cfg.browser == B.CHROME: cmd.append(f'--profile-directory={os.path.basename(get_profile_dir(cfg))}')
        else:                       cmd.extend(['--profile', get_profile_dir(cfg)])

    if cfg.args: cmd.extend(cfg.args)
    if cfg.appmode:
        url = '--app=' + KASM_URL
        if cfg.appmode != '-': url += '/#/cast/' + cfg.appmode
        cmd.append(url)

    # ---- and run it.

    rslt = run(cmd)
    if not rslt.ok:
        tmpname = f'/tmp/run_browser-{os.geteuid()}-err.out'
        with open(tmpname, 'w') as f: print(rslt.out, file=f)
        C.zwarn(f'Browser exited with statuc {rslt.returncode}.  See {tmpname}')
    else: debug(f'Browser process returned: {rslt.out}')

def pick_code(in_code):
    if not in_code:
        code = gui()
        sys.argv.append(code)  # Add to args so it'll be automatically passed to sudo (if needed)
        return code
    if in_code in CONFIGS: return in_code
    for code, cfg in CONFIGS.items():
        if in_code in cfg.aliases:
            debug(f'alias "{in_code}" mapped to code "{code}"')
            return code
    return None


def reset(cfg, post_sudo: bool):
    if not cfg.reset: return debug('config does not request reset')
    if ARGS.noreset: return C.zinfo('skipping normal reset  (--noreset)')

    if cfg.sandbox in [Sb.KASM, Sb.FIREKASM]:
        # kasm reset transports over ssh, so it must run (only) pre-sudo, for access to the base-user's ssh keys.
        if ARGS.sudo_done or post_sudo: return debug('config uses kasm and sudo already done, so deferring to pre-sudo reset')
    else:
        # non-kasm reset is overwriting files owned by the post-sudo user, so must run (only) post-sudo
        if cfg.uid and cfg.uid != CURRENT_USER: return debug('non-kasm config must wait until sudoed')

    # Once in the correct user (sudo'd or not), reset will be called twice,
    # post_sudo=False and then post_sudo=True.  We only need it to run once;
    # we'll arbitrarily pick the post_sudo=True call.
    if cfg.uid and cfg.uid == CURRENT_USER and not post_sudo:
        return debug('deferring reset until post_sudo call')

    source = get_snapshot_dir(cfg)
    dest = get_kasm_profile_dir(cfg) if cfg.sandbox in [Sb.KASM, Sb.FIREKASM] else get_profile_dir(cfg)
    rslt = run(['rsync', '-a', '--delete', source + '/', dest + '/'])
    if not rslt.ok: fatal(f'reset failed: {rslt.out}')
    else:
        if not ARGS.dryrun: quick_ok('reset ok')


def run(cmd_list, background=False, bypass_dryrun=False):
    if ARGS.dryrun and not bypass_dryrun:
        msg = f'DRYRUN: would execute: {cmd_list}'
        print(msg, file=sys.stderr)
        rslt = C.PopenOutput(ok=True, returncode=0, stdout=msg, stderr='(dryrun)', exception_str=None, pid=-1)
        return rslt
    debug('running: ' + ('(in background) ' if background else '') + str(cmd_list))
    env = os.environ.copy()
    env['GTK_IM_MODULE'] = 'xim'
    return C.popen(cmd_list, background=background, env=env)


def safedir(dir: str):  # Create this dir if needed, along with any missing parent dirs.
    if '@' in dir: return dir   # creating remote directories not supported for now.
    path = ''
    for d in dir.split('/'):
        if not d: continue
        path += '/' + d
        if not os.path.isdir(path):
            debug('creating missing dir: ' + path)
            if not ARGS.dryrun: os.mkdir(path)
    return dir


def snap_config(cfg):
    source = get_kasm_profile_dir(cfg) if cfg.sandbox in [Sb.KASM, Sb.FIREKASM] else get_profile_dir(cfg)
    dest = get_snapshot_dir(cfg)

    if BACKUP_SFX:
        dest_backup = dest + BACKUP_SFX
        debug(f'backing up snapshot {dest} -> {dest_backup}')
        rslt = run(['rsync', '-a', '--delete', dest + '/', dest_backup + '/'])
        if not rslt.ok: fatal(f'Backup "{dest}" -> "{dest_backup}" failed: {rslt.out}')

    rslt = run(['rsync', '-a', '--delete', source + '/', dest + '/'])
    if not rslt.ok: fatal(f'Snapshot to "{dest}" failed: {rslt.out}')
    print(f'snapshot saved to {dest}')
    return True


def subst(src, cfg):
    kasm_browser_profile = kasm_login = kasm_workspace = '???'
    if cfg.sandbox in [Sb.KASM, Sb.FIREKASM]: _, kasm_workspace, kasm_login, kasm_browser_profile = cfg.reset.split(':')
    b = 'google-chrome' if cfg.browser == B.CHROME else 'firefox'
    out = os.path.expanduser(src.replace('{browser}', b).                                 \
                             replace('{profile}',              cfg.profile or 'Default'). \
                             replace('{kasm_browser_profile}', kasm_browser_profile).     \
                             replace('{kasm_login}',           kasm_login).               \
                             replace('{kasm_workspace}',       kasm_workspace))
    ## if src != out: debug(f'subst "{src}" -> "{out}"')
    return out


def switch_user_if_needed(cfg, sudo_done):
    if not cfg.uid or cfg.uid == CURRENT_USER: return debug(f'already in correct uid ({CURRENT_USER})')
    if sudo_done:
        fatal(f'--sudo-done specified, but current user ({CURRENT_USER}) is wrong; should be {cfg.uid}..')
    debug(f'switching user {CURRENT_USER} -> {cfg.uid}')

    if cfg.sandbox == Sb.SNAP:
        # ---- ssh based user swap
        # SNAP => launch via ssh (snaps appear very picky about their environment,
        # and I haven't yet figured out how to get it set up "manually" in a way
        # that snaps will work yet.  But ssh seems to know the secret, so we'll
        # just launch via ssh.
        cmd0 = ('#!/bin/bash\n' +
                'DISPLAY=' + os.environ.get("DISPLAY") + ' ' +
                sys.argv[0] + ' --sudo-done ' + ' '.join(sys.argv[1:]) + '\n')
        fd, cmdfile = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            print(cmd0, file=f)
        os.chmod(cmdfile, 0o755)

        cmd = ['ssh', f'{cfg.uid}@localhost', cmdfile]
        debug(f'running loopback ssh via command file {cmdfile}: {cmd}: \n{cmd0}\n')
        out = C.popen(cmd)
        os.unlink(cmdfile)
        # browsers seem to often exit with status, which ssh passes back; ignore it.
        debug(f'browser outout: {out.out}')
        sys.exit(0)

    else:
        # ---- sudo based user swap
        sys.argv[0] = os.path.abspath(sys.argv[0])  # needs to match pathspec in sudoers
        cmd = ['/usr/bin/sudo', '--preserve-env=path', '-u', cfg.uid, '--'] + sys.argv
        cmd.append('--sudo-done')
        debug(f'sudo command: {cmd}')
        os.execv(cmd[0], cmd)    # does not return.


# ---------- gui

def gui():
    cols = ['uid', 'browser', 'sandbox', 'reset', 'profile', 'appmode', 'sync_acct', 'pw_db', 'note']
    cmd = ['zenity', '--width', '1400', '--height', '500', '--title', 'browser selection', '--list', '--column', 'code']
    for c in cols: cmd.extend(['--column', c])
    for code, cfg in CONFIGS.items():
        cmd.append(code)
        cmd.extend([str(getattr(cfg, c)).replace('Browsers.','') for c in cols])
    sel = C.popener(cmd)
    if not sel or sel.startswith('ERR'): sys.exit(f'no config selected [{sel}]')
    return sel


def fatal(msg):
    run(['zenity', '--timeout', '10', '--error', '--text', msg], background=True, bypass_dryrun=True)
    sys.exit(msg)  # prints msg to stderr


# ---------- main

def parse_args(argv):
    ap = C.argparse_epilog(description='browser launcher')
    ap.add_argument('code',            nargs='?',           help='code letter of browser config to launch.  Leave blank for gui menu')

    g1 = ap.add_argument_group('launch options')
    ap.add_argument('--debug',   '-d', action='store_true', help='explain things as they go along')
    ap.add_argument('--dryrun',  '-n', action='store_true', help='just say what would be done rather than doing it')
    g1.add_argument('--force',   '-f', action='store_true', help='skip disallowed uid combination check')
    g1.add_argument('--noreset', '-N', action='store_true', help='skip the normal reset phase for this launch')
    g1.add_argument('--purge',   '-P', default='yes',       help='[yes/no/ask] if sudo\'d to an alternate uid, kill all remaining processes of that uid after browser exits?')

    g2 = ap.add_argument_group('alternate run modes')
    g2.add_argument('--search-chrome', default=None,        help='skip normal launch, just search for a Chrome profile with this label and output its directory name')
    g2.add_argument('--search-ff',     default=None,        help='skip normal launch, just search for a Firefox profile with this label and output its directory name')
    g1.add_argument('--reset',   '-R', action='store_true', help='skip normal launch, just reset its state to the last saved snapshot')
    g1.add_argument('--snap',    '-S', action='store_true', help='skip normal launch, just snapshot its current state for the next reset')

    g3 = ap.add_argument_group('internal use only')
    g3.add_argument('--sudo-done',     action='store_true', help='do not recall this script under sudo; that is already done')
    return ap.parse_args(argv)


def main(argv=[]):
    global ARGS
    ARGS = parse_args(argv or sys.argv[1:])
    debug(f'uid: {CURRENT_USER}, {ARGS=}')

    # ---- alternate run modes that don't need a config.

    if ARGS.search_chrome:
        out = find_chrome_profile_dir(ARGS.search_chrome)
        print(out)
        return 0 if out else 1
    elif ARGS.search_ff:
        out = find_firefox_profile_dir(ARGS.search_ff)
        print(out)
        return 0 if out else 1

    # ---- get config

    code = pick_code(ARGS.code)
    cfg = CONFIGS.get(code)
    if not cfg: fatal(f'unknown code: {ARGS.code or code}')
    debug(f'{cfg=}')

    # ---- alternate run modes that need a selected config.

    if ARGS.snap:
        # For kasm-based snapshots, we must *not* change user, because we need the original user's ssh keys.
        # For normal snapshots, we must change user to have perms to save the snapshot where the reset function will expect it.
        # If we end up calling switch_user_if_needed(), the call doesn't return; it restarts the script as the new uid,
        # which runs the same logic, but won't run sudo again because of the --sudo_done flag.
        if not cfg.sandbox in [Sb.KASM, Sb.FIREKASM]: switch_user_if_needed(cfg, ARGS.sudo_done)
        ok = snap_config(cfg)
        if not ok:
            C.zwarn('error reported during snap operation')
            return 1
        quick_ok('snapped')
        return 0

    # ---- main

    reset(cfg, post_sudo=False)
    check_disallowed_uids(cfg, ARGS.force)
    switch_user_if_needed(cfg, ARGS.sudo_done)  # (if runs sudo, doesn't return; restrts the script as the new uid and with --sudo-done)
    reset(cfg, post_sudo=True)
    launch(cfg)
    cleanup()


if __name__ == '__main__': sys.exit(main())
