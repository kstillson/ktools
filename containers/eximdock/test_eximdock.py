#!/usr/bin/python3

import os, pytest, socket, time, warnings
import kcore.docker_lib as D


# ---------- fixture for container under test

@pytest.fixture(scope='session')
def container_to_test(): return D.find_or_start_container_env()


# ---------- helpers

def send_email(cookie, ip, port=2525):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    D.emit('SMTP greeting: %s' % sock.recv(1024))
    resp = D.socket_exchange(
        sock,
        ['HELO point0.net', 'MAIL FROM: tech@point0.net',
         'RCPT TO: root@point0.net', 'DATA',
         'email test cookie %s\n.\n' % cookie, 'QUIT'],
        add_eol=True, emit_transcript=True)
    sock.close()
    D.emit('SMTP responses: %s' % resp)


# ---------- tests

def test_sending_email(container_to_test):
    prod_mode = D.check_env_for_prod_mode()
    have_pswd = os.path.isfile(os.path.join(container_to_test.settings_dir, 'files/etc/exim/private.d/passwd.client'))

    cookie = D.gen_random_cookie()
    send_email(cookie, 'localhost', 25 + container_to_test.port_shift)

    time.sleep(5)
    prefix = container_to_test.vol_dir + ('/' if prod_mode else '/_rw_dv_eximdock_')

    if have_pswd:
        # If we have a real email client password, try to send the mail for real, and expect success.
        D.file_expect('Completed', prefix + 'var_log/exim/mainlog')
        D.file_expect('error', prefix + 'var_log/exim/mainlog', invert=True)
        D.file_expect('denied', prefix + 'var_log/exim/mainlog', invert=True)
        D.file_expect('Frozen', prefix + 'var_log/exim/mainlog', invert=True)
        D.file_expect(' ', prefix + 'var_log/exim/paniclog', invert=True, missing_ok=True)
        D.file_expect(' ', prefix + 'var_log/exim/rejectlog', invert=True, missing_ok=True)
        D.file_expect(cookie, prefix + 'var_mail/outbound-archive')
        print('pass')

    else:
        # Otherwise, try to send the mail, and expect it to fail
        D.file_expect('SMTP error from remote mail server', prefix + 'var_log/exim/mainlog')
        D.file_expect('Authentication Required', prefix + 'var_log/exim/mainlog')
        D.file_expect('Frozen', prefix + 'var_log/exim/mainlog')
        D.file_expect(cookie, prefix + 'var_mail/outbound-archive')
        warnings.warn('exim test passed, but in crippled mode; could not send real mail due to no credentials.')
        print('pass')
