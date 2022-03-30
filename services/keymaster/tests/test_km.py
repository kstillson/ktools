
import context_km_svc     # fix path to includes work as expected in tests

import os, random, sys, threading, time

import kcore.common as C
import ktools.kmc as kmc

import km


def test_basic_opration():
    random_high_port = random.randrange(10000,29999)
    argv = ['--certkeyfile', 'tests/server-cn=localhost.pem', '--datafile', 'tests/km-test.data.gpg', '--logfile', '-', '--port', str(random_high_port)]
    threading.Thread(target=km.main, args=(argv,), daemon=True).start()
    time.sleep(0.5)   # time for webserver to start-up

    baseurl = f'https://localhost:{random_high_port}'
    
    # password not entered yet; confirm we're "not ready"
    resp = C.web_get_e(baseurl + '/healthz', cafile='tests/server-cn=localhost.pem')
    assert resp.ok
    assert 'not ready' in resp.text

    # let's try to unlock
    resp = C.web_get_e(baseurl + '/load', cafile='tests/server-cn=localhost.pem',
                     post_dict={'password': 'test123'})
    assert resp.text == 'ok'

    resp = C.web_get_e(baseurl + '/varz?loaded-keys', cafile='tests/server-cn=localhost.pem')
    assert resp.text == '1'

    # try a successful key retreival
    os.environ['PUID'] = 'test'
    secret = kmc.query_km('testkey', override_hostname='*',
                          km_host_port=f'localhost:{random_high_port}',
                          km_cert='tests/server-cn=localhost.pem')
    assert secret == 'mysecret'

