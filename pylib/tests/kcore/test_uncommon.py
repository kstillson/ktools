
import context_kcore     # fix path to includes work as expected in tests

import io, os, sys
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


def test_gpg():
    # not supported in python2
    if sys.version_info[0] == 2: return

    crypted = UC.gpg_symmetric('hello', 'password1', decrypt=False)
    assert 'PGP MESSAGE' in crypted
    assert not 'hello' in crypted

    plain = UC.gpg_symmetric(crypted, 'password1')
    assert plain == 'hello'

    err = UC.gpg_symmetric(crypted, 'bad-password')
    assert err.startswith('ERROR:')

