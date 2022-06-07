'''Collection of less-common core routines.

There are excluded from common.py either because they're slightly obscure, and
we'd like to keep common.py reasonably compact, OR because the logic here
won't work under Circuit Python, and we'd like to keep common.py fully working
for Circuit Python.

'''

import grp, os, pwd, subprocess, sys
from dataclasses import dataclass

PY_VER = sys.version_info[0]
if PY_VER == 2: import StringIO as io
else: import io


# ----------------------------------------
# Collections of DataClasses


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
       Adds methods to support human-readable serialization and deserialzation.
    '''
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


# ----------------------------------------
# I/O

class Capture():
    '''Temporarily captures stdout and stderr and makes them available.
    Outputs an instance with .out .err.  Conversion to string gives .out
    Example usage:
      with kcore.uncommon.Capture() as cap:
      # (write stuff to stdout and/or stderr...)
      caught_stdout = cap.out
      caught_stderr = cap.err
      # (do stuff with caught_stdout, caught_stderr...)
    '''
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


def load_file_as_module(filename, desired_module_name=None):
  if not desired_module_name: desired_module_name = filename.replace('.py', '')
  import importlib.machinery, importlib.util
  loader = importlib.machinery.SourceFileLoader(desired_module_name, filename)
  spec = importlib.util.spec_from_loader(desired_module_name, loader)
  new_module = importlib.util.module_from_spec(spec)
  loader.exec_module(new_module)
  return new_module


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
    text_mode = kwargs_to_popen.get('text', True)
    if not text_mode: strip = False
    try:
        proc = subprocess.Popen(
            args, text=text_mode, stdin=subprocess.PIPE if stdin_str else None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **kwargs_to_popen)
        stdout, stderr = proc.communicate(stdin_str, timeout=timeout)
        return PopenOutput(ok=(proc.returncode == 0),
                           returncode=proc.returncode,
                           stdout=stdout.strip() if strip else stdout,
                           stderr=stderr.strip() if strip else stderr,
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


# ----------------------------------------
# GPG passthrough

def gpg_symmetric(plaintext, password, decrypt=True):
    if PY_VER == 2: return 'ERROR: not supported for python2'  # need pass_fds
    readfd, writefd = os.pipe()
    password += '\n'
    os.write(writefd, bytes(password + '\n', 'utf-8'))

    op = ['--decrypt'] if decrypt else ['--symmetric', '-a']
    cmd = ['/usr/bin/gpg'] + op + ['--passphrase-fd', str(readfd), '-o', '-', '--batch']
    p = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        pass_fds=[readfd, writefd])
    out, err = p.communicate(bytes(plaintext, 'utf-8'))
    return out.decode() if p.returncode == 0 else 'ERROR: ' + err.decode()


# ----------------------------------------
# System interaction

def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    if os.getuid() != 0: return
    running_uid = pwd.getpwnam(uid_name).pw_uid
    running_gid = grp.getgrnam(gid_name).gr_gid
    os.setgroups([])
    os.setgid(running_gid)
    os.setuid(running_uid)
    old_umask = os.umask(0o077)


