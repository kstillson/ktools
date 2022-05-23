'''Collection of less-common core routines.

There are excluded from common.py either because they're slightly obscure, and
we'd like to keep common.py reasonably compact, OR because the logic here
won't work under Circuit Python, and we'd like to keep common.py fully working
for Circuit Python.

'''

import grp, os, pwd, subprocess, sys

PY_VER = sys.version_info[0]
if PY_VER == 2: import StringIO as io
else: import io


# ----------------------------------------
# Collections of DataClasses


class DictOfDataclasses(dict):
    '''Intended for use when dict values are dataclass instances.
       Adds methods to support serialization and deserialzation.
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
       Adds methods to support serialization and deserialzation.
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


