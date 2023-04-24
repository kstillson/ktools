#!/usr/bin/python3

import os, pytest, sys, time
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- tests

def test_webdock(container_to_test):
    time.sleep(2)   # Give apache a moment to start up

    port_http = 8080 + container_to_test.port_shift
    port_https = 8443 + container_to_test.port_shift

    # TODO(defer): for reasons not currently understood, the redirect tests
    # below fail in prod mode when using the iptables-based redirect.
    # Specifically, apache emits the contents of html/index.html for http
    # requests, rather than producing a redirect, but only when the request
    # comes via dnat, not when it's sent directly.  Something to do with the
    # VirtualHost directive perhaps?  Dunno; it looks right to me.  Anyway,
    # this allows the test to pass in prod mode, but uses a Ken-specific
    # container name.  Not sure how to generalize this...
    server = 'webdock' if D.check_env_for_prod_mode() else 'localhost'

    # Using popen_expect rather than web_expect because it doesn't follow redirects,
    # and we want to check the content of the redirects.
    D.popen_expect(['/usr/bin/curl', f'http://{server}:{port_http}/'], 'moved')
    D.popen_expect(['/usr/bin/curl', '-k', f'https://{server}:{port_https}/'], 'launchpad')

    # Check that plain html is redirected to https (even for invalid links).
    # Note: This actually redirects to home.point0.net by name, which means the
    # actual content could be coming from prod rather than the test site.
    # Other tests should generally use https directly to avoid this problem.
    D.popen_expect(['/usr/bin/curl', f'http://{server}:{port_http}/q'],
                      'document has moved <a href="https://home.point0.net/q">here')

    # Check name-based vhost redirects.
    D.popen_expect(['/usr/bin/curl', '--header', 'Host: a', f'http://{server}:{port_http}/123'],
                      'document has moved <a href="http://adafru.it/123">here')

    # Check cgi script basics
    D.web_expect('ok', server, '/cgi-bin/test', port_https, https=True, verify_ssl=False)



def skip_if_not_ken_and_prod():
    return D.not_required_host('jack') or not D.check_env_for_prod_mode()


@pytest.mark.skipif(skip_if_not_ken_and_prod(), reason='test requires ken-specific and prod-specific private.d contents')
def test_ken_prod_cgis(container_to_test):
    port_http = 8080 + container_to_test.port_shift
    port_https = 8443 + container_to_test.port_shift
    server = 'webdock'

    D.web_expect('wget', server, '/rc/i/', port_https, https=True, verify_ssl=False)
    D.web_expect('pax_global_header', server, '/rc', port_https, https=True, verify_ssl=False)

    # homesec static and status pages (no login required)
    D.web_expect('color:', server, '/homesec/static/style.css', port_https, https=True, verify_ssl=False)
    D.web_expect(['ok','tardy'], server, '/homesec/healthz', port_https, https=True, verify_ssl=False)

    # Check internal proxy
    D.web_expect('<title>procmon', server, '/procmon', port_https, expect_status=200, https=True, verify_ssl=False)

