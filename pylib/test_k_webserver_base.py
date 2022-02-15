
import k_webserver_base as B
import k_varz

path1 = '/dir1/file2'
path2 = '/dir1'
path3 = '/'
paths = {path1: lambda _: '1', path2: lambda _: '2', path3: lambda _: '3'}

path1_with_get = path1 + '?x1=y1&x2=y2'

# ---------- helper functions

def context_handler(request):
    return request.context['a']

def path1_handler(request):
    assert request.full_path == path1_with_get
    assert request.method == 'test'
    assert len(request.get_params) == 2
    assert request.get_params['x1'] == 'y1'
    assert request.get_params['x2'] == 'y2'
    return 'new-handler'

def unhelpful_handler(request):
    raise Exception('failed handler')


# ---------- tests

def test_request_constructor():
    r = B.Request('TEST', path1_with_get)
    assert r.full_path == path1_with_get
    assert r.path == '/dir1/file2'
    assert r.get_params['x1'] == 'y1'
    assert r.get_params['x2'] == 'y2'

def test_response_constructor():
    assert B.Response('<html>...').msg_type == 'text/html'
    assert B.Response('just text...').msg_type == 'text'

def test_str_in_substring_list():
    assert B.str_in_substring_list('abc123', ['b'])
    assert B.str_in_substring_list('abc123', ['q', 'c', 'z'])
    assert not B.str_in_substring_list('abc123', ['q', 'z'])
    assert not B.str_in_substring_list('', ['q', 'z'])
    assert not B.str_in_substring_list('abc123', [])

def test_parse_get_params():
    d = B.parse_get_params(path1)
    assert len(d) == 0
    d = B.parse_get_params(path1_with_get)
    assert len(d) == 2
    assert d['x1'] == 'y1'
    assert d['x2'] == 'y2'

def test_finding_handlers():
    wsb = B.WebServerBase(paths, k_common_logging=False)
    assert wsb.test_handler(path1).body == '1'
    assert wsb.test_handler(path2).body == '2'
    assert wsb.test_handler(path3).body == '3'
    assert wsb.test_handler('/whatever').status_code == 404
    
    resp = wsb.test_handler(path1_with_get)
    assert resp.body == '1'
    # These should have been set by default...
    assert resp.status_code == 200
    assert resp.extra_headers == {}
    assert resp.msg_type == 'text'
    assert resp.exception is None

def test_handler_list_changes():
    wsb = B.WebServerBase(paths, k_common_logging=False)
    
    # Try removing a handler.
    assert not wsb.del_handler('non-existent-route-regex')
    assert wsb.del_handler(path1)
    assert wsb.test_handler(path1).status_code == 404
    assert wsb.test_handler(path1_with_get).status_code == 404

    # Add a single new specific handler (that does extra checks).
    path1b = path1[1:]  # Trim leading "/" to make sure it still works.
    wsb.add_handler(path1b, path1_handler)
    resp = wsb.test_handler(path1_with_get)
    assert str(resp) == '[200] new-handler'

    # Let's try adding a default handler.
    assert wsb.test_handler('/whatever').status_code == 404
    wsb.add_handlers({'.*': lambda _: 'new-default-handler'})
    resp = wsb.test_handler('/whatever')
    assert resp.status_code == 200
    assert resp.body == 'new-default-handler'

def test_multiple_hanlder_matches():
    # First one in the current list is supposed to take control.
    wsb = B.WebServerBase([('/', lambda _: 'a'), ('/', lambda _: 'b')], k_common_logging=False)
    assert wsb.test_handler('/').body == 'a'
    assert wsb.del_handler('/')
    assert wsb.test_handler('/').body == 'b'
    wsb.add_handler('/', lambda _: 'c')
    assert wsb.test_handler('/').body == 'b'
    assert wsb.del_handler('/')
    assert wsb.test_handler('/').body == 'c'
    
def test_handler_wrapping():
    wsb = B.WebServerBase([('/', unhelpful_handler)], k_common_logging=False)
    resp = wsb.test_handler('/')
    assert resp.status_code == -1
    assert str(resp.exception) == 'failed handler'
    assert resp.body is ''

def test_no_handler_wrapping():
    wsb = B.WebServerBase([('/', unhelpful_handler)], wrap_handlers=False, k_common_logging=False)
    try:
        resp = wsb.test_handler('/')
        assert 1 == 2  # That was supposed to fail.
    except Exception:
        pass

def test_varz():
    k_varz.reset()
    wsb = B.WebServerBase(paths, varz_path_trim=4, k_common_logging=False)
    wsb.add_handler('/zap', unhelpful_handler)
    wsb.test_handler(path1_with_get)
    wsb.test_handler(path2)
    wsb.test_handler(path3)
    wsb.test_handler('/whatever')
    wsb.test_handler('/zap')
    v = k_varz.VARZ
    assert v['web-server-start'] > 0
    assert v['web-path-'] == 1
    assert v['web-path-dir1'] == 2
    assert v['web-path-what'] == 1
    assert v['web-path-zap'] == 1
    assert v['web-method-test'] == 5
    assert v['web-status-200'] == 3
    assert v['web-status-404'] == 1
    assert v['web-handler-exception'] == 1

def test_context():
    wsb = B.WebServerBase([('/', context_handler)], context={'a': 'b'}, k_common_logging=False)
    assert wsb.test_handler('/').body == 'b'

def test_default_handlers():
    flags = {'flag1': 'val1', 'flag2': 'val2'}
    k_varz.reset()
    wsb = B.WebServerBase([], flagz_args=flags, k_common_logging=False)
    assert wsb.test_handler('/').status_code == 404
    assert wsb.test_handler('/favicon.ico').body == ''
    assert wsb.test_handler('/healthz').body == 'ok'
    
    resp = wsb.test_handler('/flagz')
    assert resp.status_code == 200
    assert '<td>flag1</td><td>val1</td>' in resp.body

    assert '<td>web-path-healthz</td><td>1</td>' in wsb.test_handler('/varz').body
    assert wsb.test_handler('/varz?web-path-healthz').body == '1'

def test_match_groups():
    wsb = B.WebServerBase(
        {r'/(\w+)/(\w+)/x': lambda rqst: "%s::%s" % (rqst.route_match_groups[0], rqst.route_match_groups[1])},
        k_common_logging=False)
    assert wsb.test_handler('/d1/d2/x').body == 'd1::d2'
