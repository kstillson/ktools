
import grp, os, pwd, subprocess, sys

PY_VER = sys.version_info[0]
if PY_VER == 2: import StringIO as io
else: import io


# ----------------------------------------
# I/O

'''Temporarily captures stdout and stderr and makes them available.
Outputs an instance with .out .err.  Conversion to string gives .out
Example usage:
  with k_uncommon.Capture() as cap:
    # (write stuff to stdout and/or stderr...)
    caught_stdout = cap.out
    caught_stderr = cap.err
  # (do stuff with caught_stdout, caught_stderr...)
'''
class Capture():
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


# Run a string as Python code and capture any output.
# Returns a Capture object, with added .exception field.
def exec_wrapper(cmd, locals=globals(), strip=True):
    with Capture(strip) as cap:
        try:
            exec(cmd, globals(), locals)
            cap.exception = None
            return cap
        except Exception as e:
            cap.exception = e
            return cap


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


