
'''tests for common.py'''

import io, os, sys, time
from dataclasses import dataclass

import context_kcore     # fix path to includes work as expected in tests
import kcore.varz
import kcore.common as C


# ---------- helpers

def err(msg):
    print(msg, file=sys.stderr)
    return None


# ---------- tests

# ----- cloned common.* namespace

# duplicated from test_common, just to make sure things from there still work.
def test_dict_to_list_of_pairs():
    assert C.dict_to_list_of_pairs({'b': 1, 'a': 2}) == [['a', 2], ['b', 1]]
    assert C.dict_to_list_of_pairs({}) == []


# ----- popen

def test_popen_fg():
    assert C.popen('echo 1+2 | bc', shell=True).out == '3'

    assert str(C.popen(['/usr/bin/cut', '-d:', '-f2'], 'abc:123:def')) == '123'

    assert C.popen('/bin/cat', 'hello world').out == 'hello world'

    rslt = C.popen(['/bin/ls', '/etc'])
    assert rslt.ok
    assert rslt.returncode == 0
    assert 'passwd' in str(rslt)

    rslt = C.popen(['/bin/ls', '/invalid'])
    assert not rslt.ok
    assert 'ERROR' in rslt.out
    assert rslt.returncode == 2
    assert rslt.stdout == ''
    assert 'cannot access' in rslt.stderr
    assert rslt.exception_str is None
    assert rslt.out == f'ERROR: [2] {rslt.stderr}'

    rslt = C.popen(['/invalid'])
    assert not rslt.ok
    assert str(rslt) == f'ERROR: exception: {rslt.exception_str}'
    assert 'No such file' in str(rslt)

    rslt = C.popen('echo hello', shell=True)
    assert rslt.ok
    assert rslt.stdout == str(rslt)
    assert rslt.stderr == ''
    assert rslt.exception_str is None
    assert rslt.stdout == 'hello'

    rslt = C.popen(['/bin/sleep', '3'], timeout=1)
    assert not rslt.ok
    assert rslt.stdout is None
    assert rslt.stderr is None
    assert 'timed out' in rslt.exception_str
    assert 'timed out' in str(rslt)
    try:
        os.kill(rslt.pid, 0)
        assert 'expected exception on attempt to kill timed out pid' == ''
    except:
        pass

def test_popen_bg():
    po = C.popen('sleep 1; echo "hi"', background=True, shell=True)
    assert po.ok is None
    assert po.stdout is None
    time.sleep(1.5)
    assert po.ok
    assert po.stdout == 'hi'
    assert po.stderr == ''


def test_popener():
    assert C.popener('echo 3+4|bc', shell=True) == '7'
    assert 'shadow' in C.popener(['/bin/ls', '/etc'])
    assert C.popener(['/bin/ls', '/invalid']).startswith('ERROR')
    assert 'exception' in C.popener('/bin/invalid')


# ----- Python tricks

def test_get_callers_module():
    assert C.get_callers_module().__file__ == __file__


def test_get_initial_python_file_comment():
    assert C.get_initial_python_file_comment(__file__) == 'tests for common.py'
    assert C.get_initial_python_file_comment() == 'tests for common.py'


# ----- argparse helper tests

@dataclass
class FakeArgs:
    x: str

def test_resolve_special_arg():
    args = FakeArgs('plain')
    assert C.resolve_special_arg(args, 'x') == 'plain'

    os.environ['tmp1'] = 'value1'
    args.x = '$tmp1'
    assert C.resolve_special_arg(args, 'x') == 'value1'
    assert args.x == 'value1'

    args.x = '$missing'
    try:
        C.resolve_special_arg(args, 'x')
        assert '' == 'expected exception for missing variable'
    except ValueError:
        pass

    os.environ['tmp1'] = ''
    args.x = '$tmp1'
    try:
        C.resolve_special_arg(args, 'x')
        assert '' == 'expected exception for empty required value'
    except ValueError:
        pass

    args.x = '$tmp1'
    assert C.resolve_special_arg(args, 'x', required=False) == ''
    assert args.x == ''


def test_special_arg_resolver():
    val = C.special_arg_resolver('file:testdata/file1')
    assert val == 'hello world \nline 2  \n   \n'


# ----- ad-hoc method tests

def test_random_printable():
    assert len(C.random_printable(22)) == 22
    assert C.random_printable(3, 'a') == 'aaa'

