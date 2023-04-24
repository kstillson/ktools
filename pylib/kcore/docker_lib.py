'''Container related support library.

Some highlights:
  - Return the directory with copy-on-write contents for an up container
  - Determine if the #latest image for a container is tagged #live
  - Launch a container in test mode (using d-run), or find one that's already up
  - Translate a container name to it's container id
  - A series of 'expect' style assertions for container testing, used for testing.

'''

import atexit, os, random, socket, ssl, sys, threading, time, warnings
import kcore.common as C
import ktools.ktools_settings as KS

from dataclasses import dataclass

PY_VER = sys.version_info[0]

s = KS.init(test_mode=True)
DOCKER_BIN = s.get('docker_exec')
DV_BASE = s.get('vol_base')
TEST_DV_BASE = s.get('test_vol_base')
TEST_PORT_SHIFT = KS.get('port_offset')

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

def emit(msg): print(f'>> {msg}', file=sys.stderr)


def gen_random_cookie(len=15):
    return C.random_printable(len)


def not_required_host(required_host):
    hostname = socket.gethostname()
    if hostname != required_host:
        warnings.warn(f'skipping test as contains host-specific configuration requirements. {hostname} != {required_host}')
        return True
    return False


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


# ---------- find/launch test containers

@dataclass
class ContainerData:
    name: str
    ip: str
    cow: str
    vol_dir: str
    port_shift: int
    settings_dir: str


def find_or_start_container(test_mode, name='@basedir', settings='settings.yaml'):
    # Handle case where current dir isn't the one containing the settings file.
    # (e.g. multiple pytest's run from a parent directory).
    if os.path.isfile(settings):
        settings_dir = os.path.dirname(os.path.abspath(settings))
        basedir = os.path.basename(settings_dir)
    else:
        settings_dir = os.path.dirname(C.get_callers_module(levels=3).__file__)
        settings = os.path.join(settings_dir, settings)
        if not os.path.isfile(settings): raise Exception(f'Unable to find settings file: {settings}')
        basedir = os.path.basename(settings_dir)
    if not name or name == '@basedir': name = basedir

    fullname = 'test-' + name if test_mode else name
    cid = get_cid(fullname)
    if test_mode:
        # Launch test container (if needed) on a background thread.
        if cid:
            print(f'running against existing test container {fullname} {cid}', file=sys.stderr)
        else:
            atexit.register(stop_container_at_exit, fullname)
            thread = threading.Thread(target=start_test_container, args=[settings])
            thread.daemon = True
            thread.start()
    else:
        if cid:
            print(f'running against existing prod container {fullname} {cid}', file=sys.stderr)
        else:
            warnings.warn(f'container "{fullname}" not found')

        # Assume production container is already running (and has no name prefix).
        fullname = name

    cow = find_cow_dir(fullname)

    # Give the container a moment to start if it needs it (can heavily depend on server load)
    retries = 0
    while 'error' in cow.lower() and retries < 5:
        retries += 1
        time.sleep(2)
        cow = find_cow_dir(fullname)
    if 'error' in cow.lower(): raise Exception(f'container {fullname} not found;  cow dir returned: {cow}; tried {retries} times...')

    return ContainerData(
        fullname, find_ip_for(fullname), cow,
        f'{TEST_DV_BASE}/{name}' if test_mode else f'{DV_BASE}/{name}',
        int(TEST_PORT_SHIFT) if test_mode else 0,
        settings_dir)


def check_env_for_prod_mode(control_var='KTOOLS_DRUN_TEST_PROD'):
    '''Return True if env indicates we should directly test production containers.'''
    return os.environ.get(control_var) == '1'


def find_or_start_container_env(control_var='KTOOLS_DRUN_TEST_PROD', name=None, settings='settings.yaml'):
    test_mode = not check_env_for_prod_mode(control_var)
    return find_or_start_container(test_mode, name, settings)


def start_test_container(settings='settings.yaml'):
    emit('starting test container for: ' + os.path.abspath(settings))
    rslt = C.popen(['d-run', '--test-mode', '--debug', '--settings', settings], passthrough=True)
    if not rslt.ok: emit(f'container exited with: {rslt}')
    return rslt.ok


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
def file_expect(expect, filename, invert=False, missing_ok=False):
    ok = os.path.isfile(filename)
    assert ok or missing_ok
    if missing_ok and not ok: return

    with open(filename) as f: contents = f.read()
    if expect is None:
        assert not contents, 'file was expected to be empty'
    elif invert:
        assert not expect in contents, 'found "%s" in %s when not expected' % (expect, filename)
    else:
        assert expect in contents
    return True


def file_expect_within(within_seconds, expect, filename, invert=False, missing_ok=False):
    stop_time = time.time() + within_seconds
    while True:
        try:
            ok = file_expect(expect, filename, invert=False, missing_ok=False)
            if ok: return True
        except AssertionError:
            pass
        time.sleep(1)
        assert time.time() < stop_time, f'file expectation not made within timeout: expected "{expect}" in "{filename}" within {within_seconds} secs.  Invert={invert}, missing_ok={missing_ok}'


# filename is inside the conainter.
def container_file_expect(expect, container_name, filename):
    data = C.popener([DOCKER_BIN, 'cp', '%s:%s' % (container_name, filename), '-'])
    assert not data.startswith('ERROR'), f'error getting file {container_name}:{filename}'
    assert expect in data


# expect commnd run on host (not container) to return certain output and/or error text.
def popen_expect(cmd, expect_out, expect_err=None, expect_returncode=None, send_in=None):
    rslt = C.popen(cmd, send_in)
    assert (not expect_returncode) or (rslt.returncode == expect_returncode), 'wrong returncode'
    assert (not expect_out) or (expect_out in rslt.stdout)
    assert (not expect_err) or (expect_err in rslt.stderr)


# expect commnd run inside the container to return certain output and/or error text.
def popen_inside_expect(container_name, cmd, expect_out, expect_err=None, expect_returncode=None, send_in=None):
    rslt = run_command_in_container(container_name, cmd, raw_popen=True)
    assert (not expect_returncode) or (rslt.returncode == expect_returncode), 'wrong returncode'
    assert (not expect_out) or (expect_out in rslt.stdout)
    assert (not expect_err) or (expect_err in rslt.stderr)


# launch a temporary testing container and run the provided cmd in that.
# This is provided because when launching a rootless container-under-test from
# podman, the host cannot contact the container's ports direclty.  But other
# containers on the same network can.  So we create such a container.
def testing_container_expect(cmd, expect_out, expect_err=None):
    # This needs to be kept in sync with the logic in launch_test_container()
    test_net = KS.init(test_mode=True).get('network')

    cmd2 = [DOCKER_BIN, 'run', '--rm', '-i', '--name', 'tmp_test_container', '--network', test_net, 'alpine:latest']
    return popen_expect(cmd2, expect_out, expect_err, send_in=cmd)


# expect can be a string or a list.  if list, accept ANY substring.
def web_expect(expect, server, path, port=80, expect_status=None, post_params=None, headers={}, https=False, timeout=2, size_limit=512, proxy_host=None, verify_ssl=True):
    proto = 'https' if https else 'http'
    if path[0] == '/': path = path[1:]
    url = '%s://%s:%d/%s' % (proto, server, port, path)
    resp = C.web_get(url, timeout=timeout, post_dict=post_params, verify_ssl=verify_ssl, proxy_host=proxy_host)
    if resp.exception: emit('web_get exception: %s' % resp.exception)
    assert (not expect_status) or (expect_status == resp.status_code)
    if not isinstance(expect, list):
        expect = [expect]
    for e in expect:
        if e in resp.text:
            emit('success; saw "%s" in %s' % (e, url))
            return 0
    assert False, f'no expected strings found in response: url={url}, expected: {expect}, response: {resp.text}'
