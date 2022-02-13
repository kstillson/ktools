
import io, os
import k_common as C
import k_varz as varz  ## to access varz counts in tests.


def test_dict_to_list_of_pairs():
    assert C.dict_to_list_of_pairs({'b': 1, 'a': 2}) == [['a', 2], ['b', 1]]
    assert C.dict_to_list_of_pairs({}) == []

def test_list_to_csv():
    assert C.list_to_csv([[3, 2], [2, 1, 0]]) == '3, 2\n2, 1, 0\n'
    assert C.list_to_csv(C.dict_to_list_of_pairs({'b': 1, 'a': 2})) == 'a, 2\nb, 1\n'
    assert C.list_to_csv([]) == ''

def test_read_file():
    f = 'testdata/file1'
    assert C.read_file(f) == 'hello world \nline 2  \n   \n'
    assert C.read_file(f, strip=True) == 'hello world \nline 2'
    assert C.read_file(f, list_of_lines=True) == ['hello world ', 'line 2  ', '   ', '']
    assert C.read_file(f, list_of_lines=True, strip=True) == ['hello world', 'line 2', '']
    assert C.read_file('notfound') == None
    try:
        C.read_file('notfound', wrap_exceptions=False)
        assert '' == 'exception expected!'
    except IOError:  ## py2
        pass
    except FileNotFoundError:  ## py3
        pass

def test_capture():
    with C.Capture() as cap:
        print('test1')
        C.stderr('test2')
        assert cap.out == 'test1\n'
        assert cap.err == 'test2\n'
    with C.Capture() as cap:
        assert cap.out == ''
        assert cap.err == ''

def test_exec_wrapper():
    C.init_log(logfile=None)  # Don't log errors below to a logfile.
    assert C.exec_wrapper('print(1+2)') == '3'
    a = 2
    assert C.exec_wrapper('print(a*2)', locals()) == '4'
    assert C.exec_wrapper('print(a*2)') is False
    assert C.exec_wrapper('bad-code') is False
    import k_varz as varz
    varz.set('x', 'y')  # Try pulling out of global namespace...
    assert C.exec_wrapper('print(varz.VARZ["x"])') == 'y'


# Helper function for test_logging..
# NB: depends on k_common.capture (which we tested separately above).
def check_logging(func_to_run, expect_error_count, logfile_name, expect_logfile,
                  expect_stdout, expect_stderr, expect_syslog=None):
    with C.Capture() as cap:
        func_to_run()
        assert cap.out == expect_stdout
        assert cap.err == expect_stderr
    if logfile_name:
        assert C.read_file(logfile_name) == expect_logfile
    if expect_error_count:
        assert varz.VARZ['log-error-or-higher'] == expect_error_count
    else:
        assert 'log-error-or-higher' not in varz.VARZ
    # TODO: mock syslog and check it.


def test_logging(tmp_path):
    tempname = str(tmp_path / "test.log")
    assert not os.path.isfile(tempname)

    # Basic test with all defaults except log filename.
    ok = C.init_log(logfile=tempname, force_time='TIME', clear=True)
    assert ok
    C.stderr('@@ %s' % C.LOG_FILENAME)
    check_logging(lambda: C.log('test1'),
                  0, tempname, 'INFO:log:TIME: test1\n', '', '')
    # Lets add an error-level log to that.
    check_logging(lambda: C.log_error('test2'), 1, tempname,
                  expect_logfile='INFO:log:TIME: test1\nERROR:log:TIME: test2\n',
                  expect_stdout='',
                  expect_stderr='log: ERROR: TIME: test2\n')
    assert C.last_logs() == 'ERROR: TIME: test2\nINFO: TIME: test1'

    # Test falling to basename if can't create log in bad subdir.
    expected_name = 'test123.log'
    if os.path.isfile(expected_name): os.unlink(expected_name)
    tempname2 = '/badpath/%s' % expected_name
    ok = C.init_log(logfile=tempname2, force_time='TIME', clear=True)
    assert ok
    check_logging(lambda: C.log_warning('test3'), 0, expected_name,
                  expect_logfile='WARNING:log:TIME: test3\n',
                  expect_stdout='', expect_stderr='')
    assert not os.path.isfile(tempname2)
    assert os.path.isfile(expected_name)
    os.unlink(expected_name)

    # Test disabled logfile still works for non-file destinations.
    ok = C.init_log(logfile=None, force_time='TIME', clear=True)
    assert ok
    check_logging(lambda: C.log_error('test4'), 1, None, '', expect_stdout='',
                  expect_stderr='log: ERROR: TIME: test4\n')
    assert C.last_logs() == 'ERROR: TIME: test4'


# NB: relies on the author's personal web-server.  TODO: find something better.
def test_read_web():
    assert 'hi-nossl\n' == C.read_web('http://a1.point0.net/test.html')
    assert 'hi-ssl\n' == C.read_web('https://a1.point0.net/test.html')
    assert 'hi-ssl\n' == C.read_web('https://a2.point0.net/test.html', verify_ssl=False)
    assert None == C.read_web('https://a2.point0.net/test.html')  ## ssl check faiure

    try_get = C.read_web('https://a1.point0.net/cgi-bin/test?a=b&x=y')
    assert 'a=b' in try_get
    assert 'x=y' in try_get

    try_get2 = C.read_web('https://a1.point0.net/cgi-bin/test', get_dict={'c': 'd', 'e': 'f'})
    assert 'c=d' in try_get2
    assert 'e=f' in try_get2

    try_post = C.read_web('https://a1.point0.net/cgi-bin/test', post_dict={'g': 'h', 'i': 'j'})
    assert 'g=h' in try_post
    assert 'i=j' in try_post

        
