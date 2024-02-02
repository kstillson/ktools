'''Extended common Python helpers:

  - Simplified and a very-simplied front-ends to subprocess.popen
  - cute Python trick: return an instance of the caller's module.
  - argparse helper to pull argument values from no-echo-tty, environ, or keymaster
  - argparse helper to generate help epilog from the Python file's initial comment.

  These were excluded from common.py because they're not compatible with
  Circuit Python.

  This module imports common0.* into its own namespace, so you don't need to
  separately "import common0" -- just call things for both files here.
'''

from kcore.common0 import *

import argparse, subprocess, threading
from dataclasses import dataclass


# ---------- popen API simplification wrappers

@dataclass
class PopenOutput:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    exception_str: str
    pid: int

    @property
    def out(self):
        if self.ok is None:    return None
        if self.exception_str: return 'ERROR: exception: ' + self.exception_str
        elif self.ok:          return self.stdout or ''
        else:                  return f'ERROR: [{self.returncode}] {self.stderr}'

    def __str__(self): return self.out


def popen(args, stdin_str=None, timeout=None, strip=True,
          passthrough=False, background=False, **kwargs_to_Popen):
    '''Slightly improved API for subprocess.Popen().

       args can be a simple string or a list of string args (which is safer).
       timeout is in seconds, and strip causes stdout and stderr to have any
       trailing newlines removed.

       Returns a populated PopenOutput dataclass instance.  This has all the
       various outputs in separate fields, but the idea is that all you should
       need is the .out field.  If the command worked, this will contain its
       output (by default a stripped and normal (non-binary) string), and if
       the command failed, .out will start with 'ERROR:'.

       If you indeed don't need anything other than .out, you might use
       popener() instead, which just returns the .out field directly.

       If passthrough=True, stdin and stdout are passed through to the caller,
       rather than being captured and returned in PopenOutput.

       If background=True, an PopenOutput populated with None's is returned,
       and the command is launched.  Once the command completes, it will
       populate the originally returned instance, i.e. you can detect the
       background command finished by .ok transitioning from None to True/False.
    '''
    output_instance = PopenOutput(None, None, None, None, None, None)
    if background:
        threading.Thread(target=_popen_synchronous, daemon=True,
                         args=(output_instance, args, stdin_str, timeout, strip, passthrough, kwargs_to_Popen)
                         ).start()
    else:
        _popen_synchronous(output_instance, args, stdin_str, timeout, strip, passthrough, kwargs_to_Popen)
    return output_instance


def _popen_synchronous(output_instance, args, stdin_str=None, timeout=None, strip=True,
                       passthrough=False, kwargs_to_Popen={}):
    text_mode = kwargs_to_Popen.pop('text', True)
    if not text_mode: strip = False
    stdin = kwargs_to_Popen.pop('stdin', subprocess.PIPE)
    stdout = None if passthrough else kwargs_to_Popen.pop('stdout', subprocess.PIPE)
    stderr = None if passthrough else kwargs_to_Popen.pop('stderr', subprocess.PIPE)
    try:
        proc = subprocess.Popen(
            args, text=text_mode, stdin=stdin, stdout=stdout, stderr=stderr,
            **kwargs_to_Popen)
        stdout, stderr = proc.communicate(stdin_str, timeout=timeout)
        output_instance.ok = proc.returncode == 0
        output_instance.returncode = proc.returncode
        output_instance.stdout=stdout.strip() if strip and stdout else stdout
        output_instance.stderr=stderr.strip() if strip and stderr else stderr
        output_instance.exception_str=None
        output_instance.pid=proc.pid
        return output_instance
    except Exception as e:
        try: proc.kill()
        except Exception as e2: pass
        if passthrough: print(str(e), file=sys.stderr)
        output_instance.ok = False
        output_instance.returncode = 255
        output_instance.exception_str = str(e)
        return output_instance


def popener(args, stdin_str=None, timeout=None, strip=True, **kwargs_to_popen):
    '''A very simple interface to subprocess.Popen.

       See popen (above) for fuller explaination of the arguments, but basically
       you pass the command to run in args (either a simple string or a list of
       strings).  By default you get back a non-binary stripped string with the
       output of the command, or a string that starts with 'ERROR:' if something
       went wrong.

       If you need more precise visibility into output (e.g. separating stdout
       from stderr), use popen() instead.

       Note: passing background=True will work, in that the command will run
       in the background, but because the return value is a string, it's value
       cannot be changed to the real output value once the command completes.
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


class RawFormatterWithDefaults(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass


def argparse_epilog(*args, **kwargs):
    '''Return an argparse with populated epilog matching the caller's Python file comment.'''
    module = get_callers_module(levels=2)
    epilog = get_initial_python_file_comment(module.__file__) if module else ''
    extra = kwargs.pop('epilog_extra', None)
    if extra: epilog += extra
    return argparse.ArgumentParser(epilog=epilog,
                                   formatter_class=RawFormatterWithDefaults,
                                   *args, **kwargs)


def resolve_special_arg(args, argname, required=True):
    '''Process various special argument values.  Write resolved value back into args and return it.
       See special_arg_resolver() for details on supported special values.'''

    orig_val = getattr(args, argname)
    new_value = special_arg_resolver(orig_val, argname)
    if required and not new_value: raise ValueError(f'Unable to get required value for {argname}.')
    setattr(args, argname, new_value)
    return new_value


def special_arg_resolver(input_val, argname='argument', env_value_default=None):
    '''The input value can have any of these special forms:
       - "-" to read as a password from the tty
       - $X to read the value from environment variable X
       - *A[/B/C] to query keymaster for key A (optionally under username B and password C)
       - file:X or f:X to read the value from file X
       - or can just be a normal string (which is returned unchanged)

       If $X is specified as input_val, but X is not present in the environment, then
       env_value_default will be returned.  If env_value_default is None (the default),
       a ValueError will be raised, as we have no source for the correct value.
    '''

    if not input_val: return input_val
    val = input_val

    if isinstance(val, list):
        return [special_arg_resolver(i) for i in val]

    if isinstance(val, dict):
        return {k: special_arg_resolver(v) for k, v in val.items()}

    if not isinstance(val, str): val = str(val)

    if val == "-":
        import getpass
        return  getpass.getpass(f'Enter value for {argname}: ')

    elif val.startswith('$'):
        if val.startswith('${'):
            varname, remainder = val[2:].split('}', 1)
        else:
            varname = val[1:]
            remainder = ''
        output_value = os.environ.get(varname)
        if output_value is None:
            if env_value_default is not None: return env_value_default
            raise ValueError(f'{argname} indicated to use environment variable {val}, but variable is not set and no default provided.')
        return output_value + remainder

    elif val.startswith('*'):
        parts = val[1:].split('/')
        keyname = parts[0]
        username = parts[1] if len(parts) >= 2 else None
        password = parts[2] if len(parts) >= 3 else None
        import kmc
        output_value = kmc.query_km(keyname, username, password, timeout=3, retry_limit=2, retry_delay=2)
        if output_value.startswith('ERROR:'): raise ValueError(f'failed to retrieve {keyname} from keymaster: {output_value}.')
        return output_value

    elif val.startswith('file:') or val.startswith('f:'):
        _, filename = val.split(':', 1)
        return read_file(filename, wrap_exceptions=False)

    return input_val   # Return original (which might be un-converted non-string)


# ---------- zenity-based gui helpers

def zmsg(msg, level=INFO, timeout=1.0, background=True, send_log=True, other_zenity_flags=[]):
    if send_log: log(msg, level)
    msg_type = 'error' if level == ERROR else 'warning' if level == WARNING else 'info'
    # external timeout (rather than zenity flag) to support float values.
    cmd = ['/usr/bin/timeout', str(timeout), '/usr/bin/zenity', f'--{msg_type}', '--text', msg]
    if other_zenity_flags: cmd.extend(other_zenity_flags)
    popen(cmd, background=background)

def zinfo(msg, timeout=1, background=True): return zmsg(msg, timeout=timeout, background=background)

def zwarn(msg, timeout=4, background=False): return zmsg(msg, level=WARNING, timeout=timeout, background=background)

def zfatal(msg, timeout=4):
    # background=True won't work; zenity window killed when main process exits.
    zmsg(msg, level=ERROR, timeout=timeout, background=False)
    sys.exit(msg)


# ---------- ad-hoc

# other ideas for charset: strings.printable, stings.ascii_letters, strings.digits
def random_printable(len=16, charset='0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#%+,-./:=@_'):
    import random
    return ''.join(random.choice(charset) for i in range(len))

