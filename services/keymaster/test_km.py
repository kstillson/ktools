
import os, random, sys, threading, time

import k_common as C

sys.path.insert(0, '/usr/local/bin')
import kmc

import km

def test_basic_opration():
    random_high_port = random.randrange(10000,29999)
    argv = ['--certkeyfile', 'server-cn=localhost.pem', '--logfile', '', '--port', str(random_high_port)]
    threading.Thread(target=km.main, args=(argv,), daemon=True).start()
    time.sleep(0.5)   # time for webserver to start-up

    baseurl = f'https://localhost:{random_high_port}'
    
    # password not entered yet; confirm we're "not ready"
    resp = C.web_get(baseurl + '/healthz', cafile='server-cn=localhost.pem')
    print("exception: " + str(resp.exception))
    assert resp.ok
    assert 'not ready' in resp.text

    # let's try to unlock
    resp = C.web_get(baseurl + '/load', cafile='server-cn=localhost.pem',
                     post_dict={'password': 'test123'})
    assert resp.text == 'ok'

    resp = C.web_get(baseurl + '/varz?loaded-keys', cafile='server-cn=localhost.pem')
    assert resp.text == '1'

    # try a successful key retreival
    os.environ['PUID'] = 'test'
    secret = kmc.query_km('testkey', override_hostname='localhost',
                          km_host_port=f'localhost:{random_high_port}',
                          km_cert='server-cn=localhost.pem')
    assert secret == 'mysecret'

