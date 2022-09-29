
import os, random, sys, threading, time

import context_km_svc     # fix path to includes work as expected in tests

import kcore.common as C
import kcore.auth as A
import ktools.kmc as kmc

import km

DB_PASSWD = 'test123'

def test_basic_opration(tmp_path):
    os.environ['PUID'] = 'test'

    # Start up a KM server on a local high port.   
    random_high_port = random.randrange(10000,19999)
    argv = ['--debug',
            '--certkeyfile', 'tests/server-cn=localhost.pem',
            '--datafile', 'tests/km-test.data.pcrypt',
            '--db-filename', 'tests/kcore_auth_db-test.data.pcrypt',
            '--logfile', '-',
            '--port', str(random_high_port)]
    threading.Thread(target=km.main, args=(argv,), daemon=True).start()
    time.sleep(0.5)   # time for webserver to start-up

    baseurl = f'https://localhost:{random_high_port}'
    
    # password not entered yet; confirm we're "not ready"
    resp = C.web_get_e(baseurl + '/healthz', cafile='tests/server-cn=localhost.pem')
    assert resp.ok
    assert 'not ready' in resp.text

    # let's try to unlock
    print('@@1--')
    print('@@1--', file=sys.stderr)
    resp = C.web_get_e(baseurl + '/load', cafile='tests/server-cn=localhost.pem',
                     post_dict={'password': 'test123'})
    assert resp.text == 'ok'

    resp = C.web_get_e(baseurl + '/varz?loaded-keys', cafile='tests/server-cn=localhost.pem')
    assert resp.text == '1'

    # try a successful key retreival
    print('@@2--')
    print('@@2--', file=sys.stderr)
    secret = kmc.query_km('testkey',
                          km_host_port=f'localhost:{random_high_port}',
                          km_cert='tests/server-cn=localhost.pem',
                          retry_limit=1, retry_delay=0,
                          override_hostname='test')
    assert secret == 'mysecret'
