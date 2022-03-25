
import os, socket, time
import k_uncommon as Cap

import context_pylib  # includes ../ in path so we can import things there.
import k_auth as A

# ---------- helpers

# Run a provided list of args against k_auth main and return stdout.
def cli(args, expect_status=0, expect_stderr=''):
    with Cap.Capture() as cap:
        assert A.main(args) == expect_status
        if not expect_stderr is None:
            if expect_stderr == '': assert cap.err == expect_stderr
            else: assert expect_stderr in cap.err
        return cap.out


# ---------- tests

def test_basic_operation():
    use_command = 'my command'
    use_hostname = 'myhostname'
    use_password = 'password123'
    use_username = 'myusername'
    use_time = int(time.time())

    # ---------- simple standard successful use-case

    # registration phase - client
    sec = A.generate_shared_secret(use_hostname, use_username, use_password)
    s_ver, s_host, s_user, s_hash = sec.split(':')
    assert s_ver == 'v2'
    assert s_host == use_hostname
    assert s_user == use_username
    assert len(s_hash) > 10

    # registration phase - server
    A.register_shared_secret(sec, None)

    # client side - generate token
    token = A.generate_token(use_command, use_hostname, use_username, use_password, use_time)

    # server side - check token
    ok, status, hostname, username, sent_time = A.validate_token(token, use_command)
    # print('results: %s, %s, %s, %s, %s' % (ok, status, hostname, username, sent_time))
    assert ok
    assert status == 'ok'
    assert hostname == use_hostname
    assert username == use_username
    assert sent_time == use_time

    # ---------- confirm reply prevention

    ok, status, hostname, username, sent_time = A.validate_token(token, use_command)
    assert not ok
    assert 'not later' in status
    assert hostname == use_hostname
    assert username == use_username
    assert sent_time == use_time

    # ---------- confirm disable reply prevention

    sec2 = A.get_shared_secret(use_hostname, use_username)
    assert sec2 is not None
    ok, status, hostname, username, sent_time = A.validate_token_from_secret(token, use_command, sec2, use_hostname, False, None)
    assert ok

    # ---------- confirm single byte command change breaks verification

    bad_command = use_command.replace('c', 'x')
    ok, status, hostname, username, sent_time = A.validate_token_from_secret(token, bad_command, sec2, use_hostname, False, None)
    assert not ok
    assert 'Token fails' in status


# Test the scenario where we're not differenciating between usernames,
# passwords, or even hostnames (the machine specific secret is magically
# transported to the server-side).
def test_puid_only():
    use_command = "mycommand2"

    os.environ['PUID'] = 'mypuid'
    sec = A.generate_shared_secret()
    print('generated machine-only shared secret: %s' % sec)
    assert len(sec) > 10

    token = A.generate_token_from_secret(use_command, sec)

    ok, status, hostname, username, sent_time = A.validate_token_from_secret(token, use_command, sec)
    print('results: %s, %s, %s, %s, %s' % (ok, status, hostname, username, sent_time))
    assert ok
    assert status == 'ok'
    assert username == ''

    # Regenerate machine secret with same $PUID, make sure it stays the same.
    sec2 = A.generate_shared_secret()
    assert sec == sec2

    # Regenerate machine secret with different $PUID; it should change.
    os.environ['PUID'] = 'differet-puid'
    sec3 = A.generate_shared_secret()
    assert sec != sec3


# Let's confirm the sequence we claim works in the doc..
def test_cli():
    sec = cli(['-g', '-u', 'user1', '-p', 'pass1'])
    assert socket.gethostname() in sec

    out = cli(['-r', sec])
    assert 'Done' in out

    token = cli(['-c', 'command1', '-u', 'user1', '-p', 'pass1'])
    assert token.startswith('v2:')

    out = cli(['-v', token, '-c', 'command1'])
    assert 'validated? True' in out

    os.unlink(A.DEFAULT_DB_FILENAME)
