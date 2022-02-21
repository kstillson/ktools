
import context1

import io, os, sys
import k_uncommon as UC
import k_varz

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
    k_varz.set('x', 'y')
    assert UC.exec_wrapper('print(k_varz.VARZ["x"])', globals()).out == 'y'
