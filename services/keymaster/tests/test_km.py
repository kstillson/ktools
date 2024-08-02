
import os, random, sys, threading, time

import context_km_svc     # fix path to includes work as expected in tests

import kcore.common as C
import kcore.auth as A
import ktools.kmc as kmc

import km

DB_PASSWD = 'test123'
PORT = random.randrange(10000,19999)
BASEURL = f'https://localhost:{PORT}'


# ---------- helpers

def get(path, **kwargs):
    return C.web_get_e(BASEURL + path, **kwargs, cafile='tests/server-cn=localhost.pem')

def get_key(name, **kwargs):
    return kmc.query_km(name, **kwargs,
                        km_host_port=f'localhost:{PORT}',
                        km_cert='tests/server-cn=localhost.pem',
                        retry_limit=0, retry_delay=0,
                        override_hostname='test')

def varz_check(name, expected):
    resp = get('/varz?' + name)
    assert resp.text == expected


# ---------- tests

def test_basic_opration(tmp_path):
    os.environ['PUID'] = 'test'

    # Start up a KM server on a local high port.
    argv = ['--debug',
            '--certkeyfile', 'tests/server-cn=localhost.pem',
            '--datafile',    'tests/km-test.data.pcrypt',
            '--db-filename', 'tests/kcore_auth_db-test.data.pcrypt',
            '--logfile',     '-',
            '--port',        str(PORT)]
    threading.Thread(target=km.main, args=(argv,), daemon=True).start()
    time.sleep(0.5)   # time for webserver to start-up


    # password not entered yet; confirm we're "not ready"
    resp = get('/healthz')
    assert resp.ok
    assert 'not ready' in resp.text

    # let's try to unlock
    resp = get('/load', post_dict={'password': 'test123'})
    assert resp.text == 'ok'
    varz_check('loaded-keys', '2')

    # ---- try a successful key retreival
    assert get_key('testkey') == 'mysecret'

    # ---- try successful critical key retreival
    varz_check('critical-key-touched-ouch', 'None')
    varz_check('critical-key-touched-ok', 'None')
    assert get_key('critkey') == 'mysecret2'
    varz_check('critical-key-touched-ouch', 'None')
    varz_check('critical-key-touched-ok', '1')

    # ---- try unsuccessful critical key retreival
    secret = get_key('critkey', username='wrong', password='also-wrong')
    assert secret.startswith('ERROR')
    varz_check('critical-key-touched-ouch', '1')
    varz_check('critical-key-touched-ok', '1')
    resp = get('/healthz')
    assert resp.ok
    assert 'not ready' in resp.text
