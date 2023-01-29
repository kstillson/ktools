'''Extended common Python helpers:

  - Simplified and a very-simplied front-ends to subprocess.popen
  - cute Python trick: return an instance of the caller's module.
  - argparse helper to pull argument values from no-echo-tty, environ, or keymaster
  - argparse helper to generate help epilog from the Python file's initial comment.

  These were excluded from common.py because they're not compatible with
  Circuit Python.

  This module imports common.* into its own namespace, so you don't need to
  separately "import common"- just call things for both files here.
'''

from kcore.common import *

import argparse, subprocess
from dataclasses import dataclass


# ---------- popen API simplification wrappers

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


# ---------- introspective Python tricks

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

