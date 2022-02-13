
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
    with C.Capture(strip=False) as cap:
        print('test1')
        C.stderr('test2')
        assert '%s' % cap == 'test1\n'
        assert str(cap) == 'test1\n'
        assert cap.out == 'test1\n'
        assert cap.err == 'test2\n'
    with C.Capture() as cap:
        print('test1')
        print('test2')
        assert cap.out == 'test1\ntest2'
    with C.Capture() as cap:
        assert cap.out == ''
        assert cap.err == ''

def test_exec_wrapper():
    C.init_log(logfile=None)  # Don't log errors below to a logfile.
    assert C.exec_wrapper('print(1+2)').out == '3'
    # Try passing in a local variable.
    a = 2
    assert C.exec_wrapper('print(a*2)', locals()).out == '4'
    # And now try where locals are not passed in; should cause an error.
    fail1 = C.exec_wrapper('print("to-out"); sys.stderr.write("to-err"); print(a*2)')
    assert fail1.out == 'to-out'
    assert fail1.err == 'to-err'
    assert 'not defined' in str(fail1.exception)
    # Try pulling something out of global namespace.
    import k_varz as varz
    varz.set('x', 'y')
    assert C.exec_wrapper('print(varz.VARZ["x"])').out == 'y'


# Helper function for test_logging..
# NB: depends on k_common.capture (which we tested separately above).
def check_logging(func_to_run, expect_error_count, logfile_name, expect_logfile,
                  expect_stdout, expect_stderr, expect_syslog=None):
    with C.Capture(strip=False) as cap:
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
def test_web_get():
    # Test standard response fields (check my wrapping didn't break anything).
    url = 'http://a1.point0.net/test.html'
    resp = C.web_get(url)
    ## import pdb; pdb.set_trace() ##@@
    assert resp.elapsed.microseconds > 0
    assert resp.ok
    assert 'date' in resp.headers
    assert resp.status_code == 200
    assert resp.text == 'hi-nossl\n'
    assert resp.url == url
    # Test custom added elements.
    assert resp.exception is None
    assert str(resp) == 'hi-nossl\n'

    # Test successful ssl verification.
    assert 'hi-ssl\n' == C.web_get('https://a1.point0.net/test.html').text

    # Test ssl verify failure bypass (cert is for "a1" not "a2").
    assert 'hi-ssl\n' == C.web_get('https://a2.point0.net/test.html', verify_ssl=False).text

    # Test actual ssl verification failure.
    resp = C.web_get('https://a2.point0.net/test.html')
    assert "doesn't match" in str(resp.exception)
    assert not resp.ok
    assert not resp.status_code
    assert str(resp) == ''

    # Test manually construct get params.
    assert '\na=b\n\nx=y\n\n' == C.web_get('https://a1.point0.net/cgi-bin/test?a=b&x=y').text

    # Test get_dict.
    assert '\nc=d\n\ne=f\n\n' == C.web_get('https://a1.point0.net/cgi-bin/test', get_dict={'c': 'd', 'e': 'f'}).text

    # Test post_dict.
    assert '\ng=h\n\ni=j\n\n' == C.web_get('https://a1.point0.net/cgi-bin/test', post_dict={'g': 'h', 'i': 'j'}).text


def test_read_web():
    assert 'hi-ssl\n' == C.read_web('https://a1.point0.net/test.html')


# Note: quote_plus tested indirectly by test_read_web get_dict under Python 3.
