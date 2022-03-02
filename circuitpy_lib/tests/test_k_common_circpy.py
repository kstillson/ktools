
import context_circuitpy_lib   # fixup Python include path

import os
import k_common_circpy as C
import k_log_queue as Q
import k_uncommon as UC
import k_varz as varz  ## to access varz counts in tests.


# NB: relies on the author's personal web-server.  TODO: find something better.
def test_web_get():
    # Disable ssl disabled warnings.
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Test standard response fields (check my wrapping didn't break anything).
    url = 'http://a1.point0.net/test.html'
    resp = C.web_get(url)
    assert resp.elapsed.microseconds > 0
    assert resp.ok
    assert 'date' in resp.headers
    assert resp.status_code == 200
    assert resp.text == 'hi-nossl\n'
    assert resp.url == url
    # Test custom added elements.
    assert resp.exception is None
    ##assert str(resp) == 'hi-nossl\n'

    # Test successful ssl verification.
    assert 'hi-ssl\n' == C.web_get('https://a1.point0.net/test.html').text

    # Test ssl verify failure bypass (cert is for "a1" not "a2").
    assert 'hi-ssl\n' == C.web_get('https://a2.point0.net/test.html', verify_ssl=False).text

    # Test actual ssl verification failure.
    resp = C.web_get('https://a2.point0.net/test.html')
    assert "doesn't match" in str(resp.exception)
    assert not resp.ok
    assert not resp.status_code
    ##assert str(resp) == ''

    # Test manually construct get params.
    assert '\na=b\n\nx=y\n\n' == C.web_get('https://a1.point0.net/cgi-bin/test-get?a=b&x=y').text

    # Test get_dict.
    assert '\nc=d\n\ne=f\n\n' == C.web_get('https://a1.point0.net/cgi-bin/test-get', get_dict={'c': 'd', 'e': 'f'}).text

    # Test post_dict.
    assert '\ng=h\n\ni=j\n\n' == C.web_get('https://a1.point0.net/cgi-bin/test-get', post_dict={'g': 'h', 'i': 'j'}).text


def test_read_web():
    assert 'hi-ssl\n' == C.read_web('https://a1.point0.net/test.html')


# Note: quote_plus tested indirectly by test_read_web get_dict under Python 3.
