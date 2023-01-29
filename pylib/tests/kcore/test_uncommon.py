
'''tests for uncommon.py'''

import io, os, sys, threading, time
from dataclasses import dataclass

import context_kcore     # fix path to includes work as expected in tests
import kcore.varz
import kcore.common as C
import kcore.uncommon as UC


# ---------- helpers

def err(msg):
    print(msg, file=sys.stderr)
    return None


# ---------- tests

# ----- I/O

def test_capture():
    with UC.Capture(strip=False) as cap:
        print('test1')
        err("test2")
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


def try_to_update(filename, new_contents):
    with UC.FileLock(filename):
        C.write_file(filename, new_contents)

def test_filelock(tmp_path):
    filename = str(tmp_path / 'file1')
    pq = UC.ParallelQueue()
    with UC.FileLock(filename):
        C.write_file(filename, '1')
        pq.add(try_to_update, filename, '2')
        time.sleep(0.2)
        assert C.read_file(filename, wrap_exceptions=False) == '1'
    time.sleep(0.3)
    assert C.read_file(filename) == '2'


# ----- process based tests

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


# ----- module based

def test_load_file_as_module():
    m = UC.load_file_as_module('testdata/bad-filename.py')
    assert m.data == 'hithere'


def test_load_file_into_module():
    m = UC.load_file_into_module('testdata/bad-filename.py')
    assert data == 'hithere'


# ----- rate limiter tests & infrastructure

RL_COUNT = 0
RL_COUNT_LOCK = threading.Lock()
def rl_helper_bump_count():
    global RL_COUNT, RL_COUNT_LOCK
    with RL_COUNT_LOCK:
        RL_COUNT += 1

def rl_helper_try_to_bump_count(rl, times=5):
    for _ in range(times):
        if rl.check(): rl_helper_bump_count()

def test_rate_limiter():
    rl = UC.RateLimiter(10, 1)
    threads = []
    for _ in range(10):
        t = threading.Thread(target=rl_helper_try_to_bump_count, args=(rl, ))
        threads.append(t)
        t.start()
    for t in threads: t.join()
    assert RL_COUNT == 10
    assert not rl.check()
    start_wait = time.time()
    rl.wait()
    delta = time.time() - start_wait
    assert delta > 0.5
    assert delta < 1.5


# ----- encryption

def test_symmetric_encryption():
    plaintext = 'heres my secret'
    password = 'my-password'
    salt = 'hmm-salty'

    encrypted = UC.encrypt(plaintext, password, salt)
    assert isinstance(encrypted, str)

    assert UC.decrypt(encrypted, password, salt) == plaintext
    assert UC.decrypt(encrypted, 'wrong-password', salt).startswith('ERROR')
    assert UC.decrypt(encrypted, password, 'wrong-salt').startswith('ERROR')


def test_gpg_symmetric():
    # not supported in python2
    if sys.version_info[0] == 2: return err('test_gpg_symmetric not supported in py2; skipping test.')
    # not supported if ~/.gnupg is a broken symlink
    chkpath = os.environ.get('HOME') + '/.gnupg'
    if os.path.islink(chkpath) and not os.path.exists(chkpath): return err(f'test_gpg_symmetric not supported with broken symlink {chkpath}')

    crypted = UC.gpg_symmetric('hello', 'password1', decrypt=False)
    assert 'PGP MESSAGE' in crypted
    assert not 'hello' in crypted

    plain = UC.gpg_symmetric(crypted, 'password1')
    assert plain == 'hello'

    error = UC.gpg_symmetric(crypted, 'bad-password')
    assert error.startswith('ERROR:')


# ----- parallel queue tests & infrastructure

TEST_DATA = {}
def thread_tester(delay, key, value):
    time.sleep(delay)
    global TEST_DATA
    TEST_DATA[key] = value
    return value

def test_ParallelQueue():
    q1 = UC.ParallelQueue()
    q1.add(thread_tester, 0.5, 'a', 1)
    q1.add(thread_tester, 1.0, 'a', 2)
    assert TEST_DATA.get('a') is None
    time.sleep(0.6)
    assert TEST_DATA.get('a') == 1
    time.sleep(0.6)
    assert TEST_DATA.get('a') == 2
    start_join = time.time()
    assert q1.join(1.0) == [1, 2]
    assert time.time() - start_join < 0.2

def test_ParallelQueue_join():
    q1 = UC.ParallelQueue()
    q1.add(thread_tester, 0.3, 'b', 1)
    q1.add(func=thread_tester, delay=0.2, key='b', value=2)
    q1.add(thread_tester, 0.1, key='b', value=3)
    start_join = time.time()
    assert q1.join(1.0) == [1, 2, 3]
    assert time.time() - start_join < 0.5
    assert TEST_DATA.get('b') == 1

def test_ParallelQueue_join_timeout():
    q1 = UC.ParallelQueue()
    q1.add(thread_tester, 0.1, key='c', value=1)
    q1.add(thread_tester, 1.0, 'c', 2)
    start_join = time.time()
    assert q1.join(0.3) == [1, None]
    assert time.time() - start_join < 0.5
    assert TEST_DATA.get('c') == 1

def test_ParallelQueue_single_threaded():
    q1 = UC.ParallelQueue(single_threaded=True)
    start_time = time.time()
    q1.add(thread_tester, 0.2, 'd', 1)
    t1 = time.time()
    assert t1 - start_time > 0.15
    assert t1 - start_time < 0.25
    assert TEST_DATA.get('d') == 1

    q1.add(thread_tester, 0.2, 'd', 2)
    t2 = time.time()
    assert t2 - start_time > 0.25
    assert t2 - start_time < 0.45
    assert TEST_DATA.get('d') == 2
    assert q1.join() == [1, 2]

