# Docker related support library

import atexit, glob, os, random, ssl, string, subprocess, sys
import kcore.common as C

DLIB=os.environ.get('DLIB', None)
if not DLIB:
    DLIB = '/var/lib/docker/200000.200000'
    if not os.path.isdir(DLIB): DLIB = '/var/lib/docker'

OUT = sys.stdout

# ----------------------------------------
# Intended as external command targets (generally called by ~/bin/d)


def get_cid(container_name):  # or None if container not running.
    out = subprocess.check_output(['/usr/bin/docker', 'ps', '--format', '{{.ID}} {{.Names}}', '--filter', 'name=' + container_name]).decode("utf-8")
    for line in out.split('\n'):
        if ' ' not in line: continue
        cid, name = line.split(' ', 1)
        if name == container_name: return cid
    return None


def latest_equals_live(container_name):
    try:
        ids = subprocess.check_output(
            ['/usr/bin/docker', 'images',
             '--filter=reference=kstillson/%s' % container_name,
             '--format="{{.Tag}} {{.ID}}"']).decode("utf-8").strip()
        id_map = {}
        for lines in ids.split('\n'):
            tag, did = lines.split(' ')
            id_map[tag.replace('"', '')] = did
        if id_map['latest'] == id_map['live']:
            return 'true'
        return 'false'
    except:
        return 'unknown'


def run_command_in_container(container_name, cmd):
    command = ['/usr/bin/docker', 'exec', '-u', '0', container_name]
    if isinstance(cmd, list): command.extend(cmd)
    else: command.append(cmd)
    return subprocess.check_output(command).decode("utf-8")


def find_cow_dir(container_name):
    try:
        id_prefix = subprocess.check_output(['/usr/bin/docker', 'ps', '--filter', 'name=%s' % container_name, '--format', '{{.ID}}']).decode("utf-8").replace('\n', '')
    except:
        sys.exit('cannot find container (is it up?)')
    globname = DLIB + '/image/overlay2/layerdb/mounts/%s*/mount-id' % id_prefix
    files = glob.glob(globname)
    if not files: sys.exit('ouch; docker naming convensions have changed: %s' % globname)
    with open(files[0]) as f: cow = f.read()
    return DLIB + '/overlay2/%s/diff' % cow

def get_cow_dir(container_name): return find_cow_dir(container_name)  # alias for above


# ----------------------------------------
# Testing related

def emit(msg): OUT.write('>> %s\n' % msg)

def abort(msg):
    emit(msg)
    sys.exit(msg)

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
        atexit.register(stop_container_at_exit, args)
        launch_test_container(args, extra_run_args, OUT)
        if os.fork() == 0:
            run_log_relay(args, OUT)
            sys.exit(0)

    try: ip = subprocess.check_output(['/root/bin/d', 'ip', name]).decode("utf-8").strip()
    except: ip = None
    cow = find_cow_dir(name)
    dv = '/rw/dv/%s' % name if args.prod else '/rw/dv/TMP/%s' % orig_name
    return name, ip, cow, dv

def launch_test_container(args, extra_run_args, out):
    emit('launching container ' + args.real_name)
    cmnd = ['/root/bin/d-run', '--log', 'json-file', '--tag', args.tag, '--print-cmd']
    if args.name: cmnd.extend(['--name', args.name])
    if extra_run_args: cmnd.extend(extra_run_args)
    if not args.prod:
        cmnd.extend(['--name_prefix', 'test-', '--network', 'docker2',
                     '--rm', '--subnet', '3', '-v'])
    emit(' '.join(cmnd))
    subprocess.check_call(cmnd, stdout=out, stderr=out)

def run_log_relay(args, out):
    subprocess.check_call(['/usr/bin/docker', 'logs', '-f', args.real_name], stdout=out, stderr=out)
    emit('log relay done.')


def stop_container_at_exit(args):
    if not args.run or args.prod: return False   # Don't stop something we didn't start.
    if not args.real_name: return False
    cid = get_cid(args.real_name)
    if not cid: return False    # Already stopped
    try:
        subprocess.check_call(['/usr/bin/docker', 'stop', '-t', '2', args.real_name], stdout=None, stderr=None)
        return True
    except Exception as e:
        return False

# filename is in the regular (jack host) filesystem.
def file_expect(expect, filename):
    try:
        subprocess.check_call(['/bin/fgrep', '-q', expect, filename])
        emit('success; saw "%s" in %s' % (expect, filename))
        return 0
    except:
        abort('Unable to find "%s" in: %s' % (expect, filename))

# filename is inside the conainter.
def container_file_expect(expect, container_name, filename):
    p_cat = subprocess.Popen(
        ['/usr/bin/docker', 'cp', '%s:%s' % (container_name, filename), '-'],
        stdout=subprocess.PIPE)
    p_grep = subprocess.Popen(
        ['/bin/fgrep', '-q', expect], stdin=p_cat.stdout, stdout=subprocess.PIPE)
    p_grep.communicate()
    if p_grep.returncode == 0:
        emit('success; saw "%s" in %s:%s' % (expect, container_name, filename))
        return 0
    abort('Unable to find "%s" in %s:%s' % (expect, container_name, filename))


# expect commnd run on host (not container) to return certain output and/or error text.
def popen_expect(cmd, expect_out, expect_err=None, expect_returncode=None, send_in=None):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate(send_in)
    out = out.decode("utf-8")
    err = err.decode("utf-8")
    if expect_returncode is not None and p.returncode != expect_returncode: abort('wrong return code: %d <> %d for %s' % (p.returncode, expect_returncode, cmd))
    if expect_out is not None:
        if out and not expect_out: abort('Unexpected output "%s" for: %s' % (out, cmd))
        if expect_out not in out: abort('Unable to find output "%s" in "%s" for: %s' % (expect_out, out, cmd))
    if expect_err is not None:
        if err and not expect_err: abort('Unexpected error output "%s" for: %s', (err, cmd))
        if expect_err and expect_err not in err: abort('Unable to find error "%s" in "%s" for: %s' % (expect_err, err, cmd))
    emit('success; expected output for %s' % cmd)


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


def gen_random_cookie(len=15):
    return ''.join(random.choice(string.ascii_letters) for i in range(len))

# Send a list of strings, read response after each and return in a list.
def socket_exchange(sock, send_list, add_eol=False, emit_transcript=False):
    resp_list = []
    for i in send_list:
        if emit_transcript: emit('sending: %s' % i)
        if add_eol: i += '\n'
        sock.sendall(i)
        resp = sock.recv(1024).strip()
        if emit_transcript: emit('received: %s' % resp)
        resp_list.append(resp)
    return resp_list


