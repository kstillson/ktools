'''Collection of less-common core routines.

There are excluded from common.py either because they're slightly obscure, or
to keep common.py reasonably compact, or because the logic here won't work
under Circuit Python, and I'd like to keep common.py fully working for CircuitPy.

Highlights:
  - Serialize/de-serialize helpers for dicts with RHS that are @dataclass's
  - A context manager (used with a "with" statement) for grabbing stdout/stderr
  - Helper to load files as modules (like "import" but with dynamically named files)
  - Simplified and a very-simplied front-ends to subprocess.popen
  - An in-memory multi-thread-safe rate limiter.
  - Very easy to use encrypt/decrypt for symmetric encryption w/ a provided key/salt.
  - argparse helper to pull argument values from no-echo-tty, environ, or keymaster
  - argparse helper to generate help epilog from the Python file's initial comment.
'''

import argparse, errno, grp, os, pwd, time, signal, subprocess, sys, threading
from dataclasses import dataclass

PY_VER = sys.version_info[0]
if PY_VER == 2: import StringIO as io
else: import io

# ---------- control constants

DEFAULT_SALT = 'its-bland-without-salt'


# ---------- Collections of DataClasses

class DictOfDataclasses(dict):
    '''Intended for use when dict values are dataclass instances.
       Adds methods to support human-readable serialization and deserialzation.
    '''
    def to_string(self):
        dict2 = {k: str(v) for k, v in self.items()}
        return '\n'.join([f"'{k}': {v}" for k, v in dict2.items()])

    def from_string(self, s, dataclass_type):
        locals = { dataclass_type.__name__: dataclass_type }
        count = 0
        for line in s.split('\n'):
            if not line or line.startswith('#'): continue
            if not ': ' in line: continue
            k, v_str = line.split(': ', 1)
            k = k.replace("'", "").replace('"', '')
            self[k] = eval(v_str, {}, locals)
            count += 1
        return count


class ListOfDataclasses(list):
    '''Intended for use with lists of dataclass instances.
       Adds methods to support human-readable serialization and deserialzation.'''
    def to_string(self):
        return '\n'.join([str(x) for x in self])

    def from_string(self, s, dataclass_type):
        locals = { dataclass_type.__name__: dataclass_type }
        count = 0
        for line in s.split('\n'):
            if not line or line.startswith('#'): continue
            item = eval(line, {}, locals)
            self.append(item)
            count += 1
        return count


# ---------- I/O

def getch(prompt=None, echo=True):
    if prompt: print(prompt, end='', flush=True)
    import termios, tty
    fd = sys.stdin.fileno()
    orig = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        got = sys.stdin.read(1)
        if echo: print(got, flush=True)
        return got
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, orig)


class Capture():
    '''Temporarily captures stdout and stderr and makes them available.
    Outputs an instance with .out .err.  Conversion to string gives .out
    Example usage:
      with kcore.uncommon.Capture() as cap:
      # (write stuff to stdout and/or stderr...)
      caught_stdout = cap.out
      caught_stderr = cap.err
      # (do stuff with caught_stdout, caught_stderr...)'''
    def __init__(self, strip=True):
        self._strip = strip
    def __enter__(self):
        self._real_stdout = sys.stdout
        self._real_stderr = sys.stderr
        self.stdout = sys.stdout = io.StringIO()
        self.stderr = sys.stderr = io.StringIO()
        return self
    def __exit__(self, type, value, traceback):
        sys.stdout = self._real_stdout
        sys.stderr = self._real_stderr
    def __str__(self): return self.out
    @property
    def out(self):
        o = self.stdout.getvalue()
        return o.strip() if self._strip else o
    @property
    def err(self):
        e = self.stderr.getvalue()
        return e.strip() if self._strip else e


class FileLock:
    def __init__(self, filename):
        self.lock_filename = filename + '.lock'

    def __enter__(self):
        while True:
            try:
                fd = os.open(self.lock_filename, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                return self
            except OSError as e:
                if e.errno != errno.EEXIST: raise
            time.sleep(0.3)

    def __exit__(self, type, value, trackback):
        os.unlink(self.lock_filename)


# ---------- Python file related

def get_callers_module(levels=1):
    '''Return this function caller's module instance.'''
    import inspect
    frame = inspect.stack()[levels]
    return inspect.getmodule(frame[0])


def get_initial_python_file_comment(filename=None):
    '''Parse the given Python file for it's initial long-form comment and return it.
       If filename not provided, will use the caller's filename.  Returns '' on error.
    '''
    if not filename: filename = get_callers_module(levels=2).__file__
    try:
        with open(filename) as f: data = f.read()
        return data.split("'''")[1]
    except:
        return ''


# ---------- Module-based

def load_file_as_module(filename, desired_module_name=None):
    '''Load a Python file into a new module and return the new module.

       Conceptually similar to the "import" command in Python, this allows
       you to specify the filename to load as a string.  Useful for loading
       file-lists from globs, plugins, etc.'''

    if not desired_module_name: desired_module_name = filename.replace('.py', '')
    import importlib.machinery, importlib.util
    loader = importlib.machinery.SourceFileLoader(desired_module_name, filename)
    spec = importlib.util.spec_from_loader(desired_module_name, loader)
    new_module = importlib.util.module_from_spec(spec)
    loader.exec_module(new_module)
    return new_module


def load_file_into_module(source_filename, target_module=None):
    '''Load a Python file into a specified module.

     Similar to load_file_as_module(), but rather than returning a new module,
     overrides data in a specified target_module with anything loaded from the
     source file.  If the target_module isn't specified, then the calling
     module's globals are targeted. '''

    if not os.path.isfile(source_filename): return False

    if not target_module: target_module = get_callers_module(levels=2)
    target_dict = target_module.__dict__

    mod = load_file_as_module(source_filename)
    for k, v in mod.__dict__.items():
        if k.startswith('__'): continue
        target_dict[k] = v
    return True


# ---------- Process-based

def exec_wrapper(cmd, locals=globals(), strip=True):
    '''Run a string as Python code and capture any output.
       Returns a Capture object, with added .exception field.'''
    with Capture(strip) as cap:
        try:
            exec(cmd, globals(), locals)
            cap.exception = None
            return cap
        except Exception as e:
            cap.exception = e
            return cap


def pgrep(srch):
    '''Returns a set of pids whos command matches srch.'''
    pids = popener(['pgrep', srch])
    if not pids or pids.startswith('ERROR'): return set()
    return set(pids.split('\n'))


@dataclass
class PopenOutput:
    ok: bool
    # out: str   (set by __post_init__)
    returncode: int
    stdout: str
    stderr: str
    exception_str: str
    pid: int
    def __post_init__(self):
        if self.exception_str:
            self.out = 'ERROR: exception: ' + self.exception_str
        elif self.ok and self.stdout:
            self.out = self.stdout
        else:
            self.out = f'ERROR: [{self.returncode}] {self.stderr}'
    def __str__(self): return self.out


def popen(args, stdin_str=None, timeout=None, strip=True, **kwargs_to_popen):
    '''Slightly improved API for subprocess.Popen().

       args can be a simple string or a list of string args (which is safer).
       timeout is in seconds, and strip causes stdout and stderr to have any
       trailing newlines removed.  Any other flags usually sent to
       subprocess.Popen will be carried over by kwargs_to_popen.

       Returns a populated PopenOutput dataclass instance.  This has all the
       various outputs in separate fields, but the idea is that all you should
       need is the .out field.  If the command worked, this will contain its
       output (by default a stripped and normal (non-binary) string), and if
       the command failed, .out will start with 'ERROR:'.

       If you indeed don't need anything other than .out, you might use
       popener() instead, which just returns the .out field directly.
    '''
    text_mode = kwargs_to_popen.pop('text', True)
    if not text_mode: strip = False
    stdin = kwargs_to_popen.pop('stdin', subprocess.PIPE)
    stdout = kwargs_to_popen.pop('stdout', subprocess.PIPE)
    stderr = kwargs_to_popen.pop('stderr', subprocess.PIPE)
    try:
        proc = subprocess.Popen(
            args, text=text_mode, stdin=stdin, stdout=stdout, stderr=stderr,
            **kwargs_to_popen)
        stdout, stderr = proc.communicate(stdin_str, timeout=timeout)
        return PopenOutput(ok=(proc.returncode == 0),
                           returncode=proc.returncode,
                           stdout=stdout.strip() if strip and stdout else stdout,
                           stderr=stderr.strip() if strip and stderr else stderr,
                           exception_str=None, pid=proc.pid)
    except Exception as e:
        try: proc.kill()
        except Exception as e2: pass
        return PopenOutput(ok=False, returncode=-255,
                           stdout=None, stderr=None, exception_str=str(e), pid=-1)


def popener(args, stdin_str=None, timeout=None, strip=True, **kwargs_to_popen):
    '''A very simple interface to subprocess.Popen.

       See uncommon.popen for fuller explaination of the arguments, but basically
       you pass the command to run in args (either a simple string or a list of
       strings).  By default you get back a non-binary stripped string with the
       output of the command, or a string that starts with 'ERROR:' if something
       went wrong.

       If you need more precise visibility into output (e.g. separating stdout
       from stderr), use uncommon.popen() instead.
    '''
    return popen(args, stdin_str, timeout, strip, **kwargs_to_popen).out


# ---------- Rate limiter


class RateLimiter:
    '''In-memory rate limiter.

       Tell the constructor how many events you want to allow per time period (in seconds).
       Then call check() before taking the action.  If it returns True, the action should be allowed.
    '''
    def __init__(self, rate=1, per=1.0, interthread_locking=True):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
        self._lock = threading.Lock() if interthread_locking else None

    def __str__(self):
        return f'rate:{self.rate}  per:{self.per}  allowance:{self.allowance}  last_check:{self.last_check}'

    def check_real(self):
        '''Provides the actual check, but without any locking; caller must provide that.'''
        current = time.time();
        time_passed = current - self.last_check;
        self.last_check = current;
        self.allowance += time_passed * (self.rate / self.per);
        if self.allowance > self.rate:
            self.allowance = self.rate  # throttle
        if self.allowance < 1.0:
            return False
        else:
            self.allowance -= 1.0
            return True

    def check(self):
        '''Return True if rate limit is not hit, False otherwise.  Includes locking if requested.'''
        if not self._lock: return self.check_real()
        with self._lock:
            return self.check_real()

    def wait(self, polling_interval=0.5):
        '''Wait until rate limit is cleared.  TODO(defer): calculate wait time rather than poll.'''
        while not self.check():
            time.sleep(polling_interval)


    def serialize(self):
        return f'{self.rate}, {self.per}, {self.allowance}, {self.last_check}'

    def deserialize(self, s):
        r, p, a, lc = s.split(', ')
        self.rate = float(r)
        self.per = float(p)
        self.allowance = float(a)
        self.last_check = float(lc)


# ---------- Symmetric encryption

ENCRYPTION_PREFIX = 'pcrypt1:'   # Can be used to auto-detect whether to encrypt or decrypt.

def symmetric_crypt(data, password, salt=None, decrypt=None):
    if decrypt is None: decrypt = data.startswith(ENCRYPTION_PREFIX)
    import base64
    from cryptography.fernet import Fernet
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    if not salt: salt = DEFAULT_SALT
    if decrypt: data = data.replace(ENCRYPTION_PREFIX, '')
    try:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt.encode(),
                         iterations=150000, backend=default_backend())
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        f = Fernet(key)
        in_bytes = data.encode()
        out_bytes = f.decrypt(in_bytes) if decrypt else f.encrypt(in_bytes)
        out = out_bytes.decode()
        if not decrypt: out = ENCRYPTION_PREFIX + out
        return out
    except Exception as e:
        return 'ERROR: ' + (str(e) or 'invalid password or salt')

def encrypt(plaintext, password, salt=None):
    return symmetric_crypt(plaintext, password, salt, decrypt=False)

def decrypt(encrypted, password, salt=None):
    return symmetric_crypt(encrypted, password, salt, decrypt=True)

# -----

def gpg_symmetric(plaintext, password, decrypt=True):
    if PY_VER == 2: return 'ERROR: not supported for python2'  # need pass_fds

    gpg_pids_initial = pgrep('gpg-agent')

    readfd, writefd = os.pipe()
    password += '\n'
    os.write(writefd, bytes(password + '\n', 'utf-8'))

    op = ['--decrypt'] if decrypt else ['--symmetric', '-a']
    cmd = ['/usr/bin/gpg'] + op + ['--passphrase-fd', str(readfd), '-o', '-', '--batch']
    p = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        pass_fds=[readfd, writefd])
    out, err = p.communicate(bytes(plaintext, 'utf-8'))

    # Kill any gpg-agent processes which were launched by us.
    gpg_pids_final = pgrep('gpg-agent')

    for pid in gpg_pids_final - gpg_pids_initial:
        os.kill(int(pid), signal.SIGTERM)

    return out.decode() if p.returncode == 0 else 'ERROR: ' + err.decode()


# ---------- System interaction

def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    if os.getuid() != 0: return
    running_uid = pwd.getpwnam(uid_name).pw_uid
    running_gid = grp.getgrnam(gid_name).gr_gid
    os.setgroups([])
    os.setgid(running_gid)
    os.setuid(running_uid)
    old_umask = os.umask(0o077)


# ---------- Parallel queue

class ParallelQueue:
    '''Run a bunch of functions in parallel, and support waiting for all to finish.'''

    def __init__(self, single_threaded=False):
        self.single_threaded = single_threaded
        self.counter = 0
        self.threads = []
        self.timed_out = False
        self.returns = {}

    def add(self, func, *args, **kwargs):
        if self.single_threaded:
            self.returns[self.counter] = func(*args, **kwargs)
            self.counter += 1
            return
        kwargs['_func'] = func
        kwargs['_id'] = self.counter
        self.counter += 1
        thread = threading.Thread(target=self.run_wrapper, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        self.threads.append(thread)

    def run_wrapper(self, *args, **kwargs):
        _id = kwargs.pop('_id')
        func = kwargs.pop('_func')
        tmp = func(*args, **kwargs)
        self.returns[_id] = tmp

    def join(self, timeout=None):   # timeout is a float in seconds.
        '''Wait for all to finish.  timeout is a float in seconds.
           Returns a list of return values in order of additions.'''
        if not self.single_threaded:
            for t in self.threads:
                t.join(timeout=timeout)
                if t.is_alive():
                    self.timed_out = True
                    timeout = 0.0
        out = [self.returns.get(i) for i in range(self.counter)]
        return out


# ---------- Argparse helpers

def argparse_epilog(*args, **kwargs):
    '''Return an argparse with populated epilog matching the caller's Python file comment.'''
    filename = get_callers_module(levels=2).__file__
    return argparse.ArgumentParser(epilog=get_initial_python_file_comment(filename),
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   *args, **kwargs)


def resolve_special_arg(args, argname, required=True):
    '''Process various special argument values.  Write resolved value back into args and return it.

       args.argname can be "-" to read as a password from tty,
       $X to indicate to use environment variable as value,
       *A[/B/C] to query keymaster for key A under username B and password C,
       or can just be a normal string.
    '''
    arg_val = getattr(args, argname)
    if arg_val == "-":
        import getpass
        value = getpass.getpass(f'Enter value for {argname}: ')
        setattr(args, argname, value)

    elif arg_val and arg_val.startswith('$'):
        varname = arg_val[1:]
        value = os.environ.get(varname)
        if value is None: raise ValueError(f'{argname} indicated to use environment variable {arg_val}, but variable is not set.')
        setattr(args, argname, value)

    elif arg_val and arg_val.startswith('*'):
        parts = arg_val[1:].split('/')
        keyname = parts[0]
        username = parts[1] if len(parts) >= 2 else None
        password = parts[2] if len(parts) >= 3 else None
        import kmc
        arg_val = kmc.query_km(keyname, username, password, timeout=3, retry_limit=2, retry_delay=2)
        if arg_val.startswith('ERROR:'): raise ValueError(f'failed to retrieve {keyname} from keymaster: {arg_val}.')
        setattr(args, argname, value)

    else: value = arg_val

    if required and not value: raise ValueError(f'Unable to get required value for {argname}.')
    return value

