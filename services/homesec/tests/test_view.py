
import context_homesec     # fix path to includes work as expected in tests

import base64
import kcore.common as C
import kcore.webserver as W

import view as V


# ---------- testing infrastructure

def fake_password_checker(user, passwd):
    return 'secret' in passwd


# ---------- tests

def test_basic_auth():
    V.PASSWORD_CHECKER = fake_password_checker
    
    fake_request = W.Request('GET', '/test')  # no attempt to log in
    resp = V.test_view(fake_request)
    assert resp.status_code == 401

    fake_request.headers['Authorization'] = 'homesec ' + base64.b64encode(
        bytes(f'myusername:mysecret', encoding='ascii')).decode('ascii')
    resp = V.test_view(fake_request)
    assert resp == 'hello myusername'

    
def test_template():
    V.TEMPLATE_DIR = 'tests'
    out = V.render('template_test.html', {'something': 'fun'})
    assert out == 'this is a lot of fun.\n'


def test_static_view():
    V.STATIC_DIR = 'tests'
    fake_request = W.Request('GET', '/static/template_test.html')
    resp = V.static_view(fake_request)
    assert resp == 'this is a lot of {{ something }}.\n'

    fake_request = W.Request('GET', '/static/nonexistent')
    resp = V.static_view(fake_request)
    assert resp.body == 'file not found'
    assert resp.status_code == 404

    fake_request = W.Request('GET', 'invalid')
    resp = V.static_view(fake_request)
    assert resp.status_code == 400

