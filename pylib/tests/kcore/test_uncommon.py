
import io, os, sys
from dataclasses import dataclass

import context_kcore     # fix path to includes work as expected in tests
import kcore.varz
import kcore.uncommon as UC


def test_capture():
    with UC.Capture(strip=False) as cap:
        print('test1')
        sys.stderr.write("test2\n")
        assert '%s' % cap == 'test1\n'
        assert str(cap) == 'test1\n'
        assert cap.out == 'test1\n'
        assert cap.err == 'test2\n'
    with UC.Capture() as cap:
        print('test1')
        print('test2')
        assert cap.out == 'test1\ntest2'
    with UC.Capture() as cap:
        assert cap.out == ''
        assert cap.err == ''

@dataclass
class T1:
    a: str
    b: int

def test_dict_of_dataclasses():
    d = UC.DictOfDataclasses({'k1': T1('a1', 1), 'k2': T1('b2', 2)})
    s = d.to_string()
    d2 = UC.DictOfDataclasses()
    assert d2.from_string(s, T1) == 2
    assert d2['k1'].a == 'a1'
    assert d2['k2'].b == 2

def test_list_of_dataclasses():
    l1 = UC.ListOfDataclasses([T1('a1', 1), T1('b2', 2)])
    s = l1.to_string()
    l2 = UC.ListOfDataclasses()
    assert l2.from_string(s, T1) == 2
    assert l2[0].a == 'a1'
    assert l2[0].b == 1
    assert l2[1].a == 'b2'
    assert l2[1].b == 2


def test_exec_wrapper():
    assert UC.exec_wrapper('print(1+2)').out == '3'
    # Try passing in a local variable.
    a = 2
    assert UC.exec_wrapper('print(a*2)', locals()).out == '4'
    # And now try where locals are not passed in; should cause an error.
    fail1 = UC.exec_wrapper('print("to-out"); sys.stderr.write("to-err"); print(a*2)')
    assert fail1.out == 'to-out'
    assert fail1.err == 'to-err'
    assert 'not defined' in str(fail1.exception)
    # Try pulling something out of global namespace.
    kcore.varz.set('x', 'y')
    assert UC.exec_wrapper('print(kcore.varz.VARZ["x"])', globals()).out == 'y'


def test_load_file_as_module():
    m = UC.load_file_as_module('testdata/bad-filename.py')
    assert m.data == 'hithere'


def test_popen():
    assert UC.popen('echo 1+2 | bc', shell=True).out == '3'

    assert str(UC.popen(['/usr/bin/cut', '-d:', '-f2'], 'abc:123:def')) == '123'

    assert UC.popen('/bin/cat', 'hello world').out == 'hello world'

    rslt = UC.popen(['/bin/ls', '/etc'])
    assert rslt.ok
    assert rslt.returncode == 0
    assert 'passwd' in str(rslt)

    rslt = UC.popen(['/bin/ls', '/invalid'])
    assert not rslt.ok
    assert 'ERROR' in rslt.out
    assert rslt.returncode == 2
    assert rslt.stdout == ''
    assert 'cannot access' in rslt.stderr
    assert rslt.exception_str is None
    assert rslt.out == f'ERROR: [2] {rslt.stderr}'

    rslt = UC.popen(['/invalid'])
    assert not rslt.ok
    assert str(rslt) == f'ERROR: exception: {rslt.exception_str}'
    assert 'No such file' in str(rslt)

    rslt = UC.popen('echo hello', shell=True)
    assert rslt.ok
    assert rslt.stdout == str(rslt)
    assert rslt.stderr == ''
    assert rslt.exception_str is None
    assert rslt.stdout == 'hello'

    rslt = UC.popen(['/bin/sleep', '3'], timeout=1)
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


def test_popener():
    assert UC.popener('echo 3+4|bc', shell=True) == '7'
    assert 'shadow' in UC.popener(['/bin/ls', '/etc'])
    assert UC.popener(['/bin/ls', '/invalid']).startswith('ERROR')
    assert 'exception' in UC.popener('/bin/invalid')


def test_symmetric_encryption():
    plaintext = 'heres my secret'
    password = 'my-password'
    salt = 'hmm-salty'

    encrypted = UC.encrypt(plaintext, password, salt)
    assert isinstance(encrypted, str)

    assert UC.decrypt(encrypted, password, salt) == plaintext
    assert UC.decrypt(encrypted, 'wrong-password', salt).startswith('ERROR')
    assert UC.decrypt(encrypted, password, 'wrong-salt').startswith('ERROR')
    
    
    
''' TODO: DISABLED.
    calling gpg via subprocess requires /usr/bin/gpg-agent, which I've disabled
    on my system, which causes this test to fail.  Disabling for now.
    This test does pass if gpg-agent is enabled.

def test_gpg_symmetric():
    # not supported in python2
    if sys.version_info[0] == 2: return

    crypted = UC.gpg_symmetric('hello', 'password1', decrypt=False)
    assert 'PGP MESSAGE' in crypted
    assert not 'hello' in crypted

    plain = UC.gpg_symmetric(crypted, 'password1')
    assert plain == 'hello'

    err = UC.gpg_symmetric(crypted, 'bad-password')
    assert err.startswith('ERROR:')

'''
