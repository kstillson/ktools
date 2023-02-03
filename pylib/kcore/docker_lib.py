'''Container related support library.

Some highlights:
  - Return the directory with copy-on-write contents for an up container
  - Determine if the #latest image for a container is tagged #live
  - Launch a container in test mode (using d-run), or find one that's already up
  - Translate a container name to it's container id
  - A series of 'expect' style assertions for container testing, used for testing.

'''

import atexit, os, random, ssl, string, sys, threading, time
import kcore.common as C

from dataclasses import dataclass

PY_VER = sys.version_info[0]

DOCKER_BIN = os.environ.get('DOCKER_EXEC', 'docker')
DV_BASE = os.environ.get('DOCKER_VOL_BASE', '/rw/dv')

# Testing related
OUT = sys.stdout


# ----------------------------------------
# Intended as external command targets (generally called by ~/bin/d)

def get_cid(container_name):  # or None if container not running.
    out = C.popener([DOCKER_BIN, 'ps', '--format', '{{.ID}} {{.Names}}', '--filter', 'name=' + container_name])
    for line in out.split('\n'):
        if ' ' not in line: continue
        cid, name = line.split(' ', 1)
        if name == container_name: return cid
    return None


def latest_equals_live(container_name):
    try:
        ids = C.popener(
            [DOCKER_BIN, 'images', '--filter=reference=ktools/%s' % container_name,
             '--format="{{.Tag}} {{.ID}}"'])
        id_map = {}
        for lines in ids.split('\n'):
            tag, did = lines.split(' ')
            id_map[tag.replace('"', '')] = did
        if id_map['latest'] == id_map['live']:
            return 'true'
        return 'false'
    except:
        return 'unknown'


def run_command_in_container(container_name, cmd, raw_popen=False):
    command = [DOCKER_BIN, 'exec', '-u', '0', container_name]
    if isinstance(cmd, list): command.extend(cmd)
    else: command.append(cmd)
    return C.popen(command) if raw_popen else C.popener(command)


def find_cow_dir(container_name):
    try:
        upperdir_json = C.popener(f'{DOCKER_BIN} inspect {container_name} | fgrep UpperDir', shell=True).strip()
    except:
        sys.exit('cannot find container (is it up?)')
    key, val = upperdir_json.split(': ', 1)
    return val.replace('",', '').replace('"', '')


def find_ip_for(name): return C.popener(['d', 'ip', name])

def get_cow_dir(container_name): return find_cow_dir(container_name)  # alias for find_cow_dir


# ----------------------------------------
# Testing related

# ---------- general support

def abort(msg):
    emit(msg)
    sys.exit(msg)


def emit(msg): OUT.write('>> %s\n' % msg)


def gen_random_cookie(len=15):
    return ''.join(random.choice(string.ascii_letters) for i in range(len))


# Send a list of strings, read response after each and return in a list.
# (used for things like exchanging interactive commands with a remote SMTP server non-interactively)
def socket_exchange(sock, send_list, add_eol=False, emit_transcript=False):
    resp_list = []
    for i in send_list:
        if emit_transcript: emit('sending: %s' % i)
        if add_eol: i += '\n'
        if PY_VER == 3: i = i.encode('utf-8')
        sock.sendall(i)
        resp = sock.recv(1024)
        if PY_VER == 3: resp = resp.decode('utf-8')
        resp = resp.strip()
        if emit_transcript: emit('received: %s' % resp)
        resp_list.append(resp)
    return resp_list


# ---------- THE NEW WAY @@

@dataclass
class ContainerData:
    name: str
    ip: str
    cow: str
    vol_dir: str
    port_shift: int


def find_or_start_container(test_mode, name='@basedir', settings='settings.yaml'):
    # Handle case where current dir isn't the one containing the settings file.
    # (e.g. multiple pytest's run from a parent directory).
    if os.path.isfile(settings):
        basedir = os.path.basename(os.path.dirname(os.path.abspath(settings)))
    else:
        settings_dir = os.path.dirname(C.get_callers_module(levels=3).__file__)
        settings = os.path.join(settings_dir, settings)
        if not os.path.isfile(settings): raise Exception(f'Unable to find settings file: {settings}')
        basedir = os.path.basename(settings_dir)
    if name == '@basedir': name = basedir

    fullname = 'test-' + name if test_mode else name
    cid = get_cid(fullname)
    if test_mode:
        # Launch test container (if needed) on a background thread.
        if cid:
            print(f'running against existing test container {fullname} {cid}', file=sys.stderr)
        else:
            atexit.register(stop_container_at_exit, fullname)
            thread = threading.Thread(target=start_test_container, args=[name, settings])
            thread.daemon = True
            thread.start()
            time.sleep(2)  # Give time for container to start.
    else:
        if cid:
            print(f'running against existing prod container {fullname} {cid}', file=sys.stderr)
        else:
            print(f'warning: container "{fullname}" not found', file=sys.stderr)

        # Assume production container is already running (and has no name prefix).
        fullname = name

    # TODO(defer): ideally, at least the vol_dir and port_shift fields should
    # be populated by getting that data our of the d-run command rather than
    # manually re-creating it here.  But we run d-run foreground/syncronously
    # (better for watching test results unfold), so getting any output from it
    # would be tricky.  Oh well.
    #
    return ContainerData(
        name, find_ip_for(fullname), find_cow_dir(fullname),
        f'{DV_BASE}/TMP/{name}' if test_mode else f'{DV_BASE}/{name}',
        10000 if test_mode else 0)


def find_or_start_container_env(control_var='KTOOLS_DRUN_TEST_PROD', name='@basedir', settings='settings.yaml'):
    test_mode = os.environ.get(control_var) != '1'
    return find_or_start_container(test_mode, name, settings)


def start_test_container(name, settings='settings.yaml'):
    emit('starting test container for: ' + name)
    rslt = C.popen(['d-run', '--test-mode', '--name', name, '--settings', settings, '--print-cmd'])
    emit(f'container exited;  results: {rslt}')
    return rslt.ok


# ---------- THE OLD WAY @@ (deprecation pending)

# ---------- launching/manipulating containers-under-test

def add_testing_args(ap):
    ap.add_argument('--name', '-n', help='Override default name of container to launch and/or test')
    ap.add_argument('--out',  '-o', default='-', help='Where to send all output generated by the test')
    ap.add_argument('--prod', '-p', action='store_true', help='Test the production container, rather than the dev container')
    ap.add_argument('--run',  '-r', action='store_true', help='Start up the container to test')
    ap.add_argument('--tag',  '-t', default='latest', help='If using --run, what image tag to launch')


def launch_or_find_container(args, extra_run_args=None):
    global OUT
    name = orig_name = args.name or os.path.basename(os.getcwd())
    if not args.prod: name = 'test-' + name
    args.real_name = name

    if args.out == '-':
        OUT = sys.stdout
    else:
        dir = os.path.dirname(args.out)
        if dir and not os.path.isdir(dir):
            os.mkdir(dir)
            os.chown(dir, 200000, 200000)
        OUT = open(args.out, 'w')

    if args.run:
        if os.fork() == 0:
            launch_test_container(args, extra_run_args, OUT)
            run_log_relay(args, OUT)
            sys.exit(0)
        else:
            atexit.register(stop_container_at_exit, name)

    time.sleep(1)  #  Give container a chance to launch.
    try: ip = C.popener(['d', 'ip', name])
    except: ip = None
    cow = find_cow_dir(name)
    dv = '/rw/dv/%s' % name if args.prod else '/rw/dv/TMP/%s' % orig_name
    return name, ip, cow, dv


def launch_test_container(args, extra_run_args, out):
    emit('launching container ' + args.real_name)
    cmnd = ['d-run', '--tag', args.tag, '--print-cmd']
    if args.name: cmnd.extend(['--name', args.name])
    if extra_run_args: cmnd.extend(extra_run_args)
    test_net = os.environ.get('KTOOLS_DRUN_TEST_NETWORK') or 'bridge'
    if not args.prod:
        cmnd.extend(['--name_prefix', 'test-', '--network', test_net, '--rm=1', '-v'])
    if test_net == 'docker2':  ## TODO(defer): kds specific
        cmnd.extend(['--subnet', '3'])
    emit(' '.join(cmnd))
    rslt = C.popen(cmnd, stdout=out, stderr=out)
    if not rslt.ok: sys.exit(rslt.out)


def run_log_relay(args, out):
    rslt = C.popen([DOCKER_BIN, 'logs', '-f', args.real_name], stdout=out, stderr=out)
    if not rslt.ok: sys.exit(rslt.out)
    emit('log relay done.')


def stop_container_at_exit(name):
    if not get_cid(name):
        print(f'container {name} already stopped.', file=sys.stderr)
        return False    # Already stopped
    print(f'stopping container {name}.', file=sys.stderr)
    rslt = C.popener([DOCKER_BIN, 'stop', '-t', '2', name])
    if rslt.startswith('ERROR'):
        print(f'error stopping container {name}: {rslt}', file=sys.stderr)
        return False
    return True


# ---------- assertions

# filename is in the regular host filesystem.
# returns error message of None if all ok.
def file_expect_real(expect, filename, invert=False, missing_ok=False):
    ok = os.path.isfile(filename)
    if not ok:
        if missing_ok: return emit('success; file %s missing, and thats ok.' % filename)
        else: abort('file %s not found' % filename)

    with open(filename) as f: contents = f.read()
    if expect is None:
        if not contents: return emit('file %s empty, as expected' % filename)
        else: abort('file %s not empty, but was expected to be.' % filename)
    if invert:
        if not expect in contents: return emit('success; "%s" NOT in %s, as expected' % (expect, filename))
        else: abort('found "%s" in %s when not expected' % (expect, filename))
    if expect in contents: return emit('success; "%s" in %s, as expected' % (expect, filename))
    else: abort('Unable to find "%s" in: %s' % (expect, filename))


def file_expect(expect, filename, invert=False, missing_ok=False):
    err = file_expect_real(expect, filename, invert=False, missing_ok=False)
    if err: abort(err)
    return True

def file_expect_within(within_seconds, expect, filename, invert=False, missing_ok=False):
    stop_time = time.time() + within_seconds
    while time.time() < stop_time:
        err = file_expect_real(expect, filename, invert=False, missing_ok=False)
        if not err: return True
        time.sleep(1)
    # If we get to here, we time-out, so reflect the most recent error as fatal.
    abort(err)


# filename is inside the conainter.
def container_file_expect(expect, container_name, filename):
    data = C.popener([DOCKER_BIN, 'cp', '%s:%s' % (container_name, filename), '-'])
    if data.startswith('ERROR'): abort('error getting file %s:%s' % (container_name, filename))
    if expect in data:
        emit('success; saw "%s" in %s:%s' % (expect, container_name, filename))
        return 0
    abort('Unable to find "%s" in %s:%s' % (expect, container_name, filename))


# expect commnd run on host (not container) to return certain output and/or error text.
def popen_expect(cmd, expect_out, expect_err=None, expect_returncode=None, send_in=None):
    rslt = C.popen(cmd, send_in)
    if expect_returncode is not None and rslt.returncode != expect_returncode: abort('wrong return code: %d <> %d for %s' % (rslt.returncode, expect_returncode, cmd))
    if expect_out is not None:
        if rslt.stdout and not expect_out: abort('Unexpected output "%s" for: %s' % (rslt.stdout, cmd))
        if expect_out not in rslt.stdout: abort('Unable to find output "%s" in "%s" for: %s' % (expect_out, rslt.stdout, cmd))
    if expect_err is not None:
        if rslt.stderr and not expect_err: abort('Unexpected error output "%s" for: %s', (rslt.stderr, cmd))
        if expect_err and expect_err not in rslt.stderr: abort('Unable to find error "%s" in "%s" for: %s' % (expect_err, rslt.stderr, cmd))
    emit('success; expected output for %s' % cmd)


# expect commnd run inside the container to return certain output and/or error text.
def popen_inside_expect(container_name, cmd, expect_out, expect_err=None, expect_returncode=None, send_in=None):
    rslt = run_command_in_container(container_name, cmd, raw_popen=True)
    if expect_returncode is not None and rslt.returncode != expect_returncode: abort('wrong return code: %d <> %d for %s' % (rslt.returncode, expect_returncode, cmd))
    if expect_out is not None:
        if rslt.stdout and not expect_out: abort('Unexpected output "%s" for: %s' % (rslt.stdout, cmd))
        if expect_out not in rslt.stdout: abort('Unable to find output "%s" in "%s" for: %s' % (expect_out, rslt.stdout, cmd))
    if expect_err is not None:
        if rslt.stderr and not expect_err: abort('Unexpected error output "%s" for: %s', (rslt.stderr, cmd))
        if expect_err and expect_err not in rslt.stderr: abort('Unable to find error "%s" in "%s" for: %s' % (expect_err, rslt.stderr, cmd))
    emit('success; expected output for %s' % cmd)


# launch a temporary testing container and run the provided cmd in that.
# This is provided because when launching a rootless container-under-test from
# podman, the host cannot contact the container's ports direclty.  But other
# containers on the same network can.  So we create such a container.
def testing_container_expect(cmd, expect_out, expect_err=None):
    # This needs to be kept in sync with the logic in launch_test_container()
    test_net = os.environ.get('KTOOLS_DRUN_TEST_NETWORK') or 'bridge'

    cmd2 = [DOCKER_BIN, 'run', '--rm', '-i', '--name', 'tmp_test_container', '--network', test_net, 'alpine:latest']
    return popen_expect(cmd2, expect_out, expect_err, send_in=cmd)


# expect can be a string or a list.  if list, accept any substring.
def web_expect(expect, server, path, port=80, expect_status=None, post_params=None, headers={}, https=False, timeout=2, size_limit=512, proxy_host=None, verify_ssl=True):
    proto = 'https' if https else 'http'
    if path[0] == '/': path = path[1:]
    url = '%s://%s:%d/%s' % (proto, server, port, path)
    resp = C.web_get(url, timeout=timeout, post_dict=post_params, verify_ssl=verify_ssl, proxy_host=proxy_host)
    if resp.exception: emit('web_get exception: %s' % resp.exception)
    if expect_status and expect_status != resp.status_code:
        abort('Web get returned unexpected status: %s : %s <> %s' % (url, expect_status, resp.status_code))
    if not isinstance(expect, list):
        expect = [expect]
    for e in expect:
        if e in resp.text:
            emit('success; saw "%s" in %s' % (e, url))
            return 0
    abort('Unable to find "%s" in: %s; response: %s' % (expect, url, resp.text))


