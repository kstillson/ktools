#!/usr/bin/python3

import os, pytest, warnings
import kcore.docker_lib as D
import ktools.kmc as kmc


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_keymaster(container_to_test):
    prod_mode = D.check_env_for_prod_mode()
    if prod_mode:
        warnings.warn('cannot do in-place prod testing; test is destructive to its container.')
        return

    server = 'localhost'
    test_port = 4444 + container_to_test.port_shift
    
    # Try retrieving the test key before decrypting the database; should fail.
    D.web_expect('not ready', server, '/testkey', port=test_port, https=True, verify_ssl=False)

    # Decrypt the database with the test password, should say we're ok.
    D.web_expect('ok', server, '/load', post_params={'password': 'test123'}, port=test_port, https=True, verify_ssl=False)

    # Try retrieving the same test key.  Should work now.
    os.environ['PUID'] = 'test'
    kmc.DEBUG = True
    hostport = '%s:%d' % (server, test_port)
    answer = kmc.query_km('testkey', km_host_port=hostport, km_cert='', timeout=2, retry_limit=0, override_hostname='test')
    assert answer == 'mysecret'

    # Check the service health.
    D.web_expect('ok', server, '/healthz', port=test_port, https=True, verify_ssl=False)

    # On-demand clear of the decrypted database.
    D.web_expect('zapped', server, '/qqq', port=test_port, https=True, verify_ssl=False)

    # And now a health check should indicate "not ready".
    D.web_expect('not ready', server, '/testkey', port=test_port, https=True, verify_ssl=False)

    # Now lets re-start the database and try for a bad key, which should fail
    # and leave the system locked due to a source IP check failure.
    D.web_expect('ok', server, '/load', post_params={'password': 'test123'}, port=test_port, https=True, verify_ssl=False)
    answer = kmc.query_km('nonexistent-key', km_host_port=hostport, km_cert='', timeout=2, retry_limit=0)
    assert 'ERROR: no such key' in answer

    # The system should now be locked.
    answer = kmc.query_km('testkey', km_host_port=hostport, km_cert='', timeout=2, retry_limit=0)
    assert 'not ready' in answer, 'expected system to be locked, but did not see "not ready" error'
    D.web_expect('not ready', server, '/test', port=test_port, https=True, verify_ssl=False)
    
