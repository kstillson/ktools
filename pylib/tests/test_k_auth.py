
import context_pylib  # includes ../ in path so we can import things there.

import os, socket, time
import k_uncommon as Cap

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
    A.register(sec, None)

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

    shared_secret = A.get_shared_secret_from_db(use_hostname, use_username)
    assert shared_secret is not None
    ok, status, hostname, username, sent_time = A.validate_token_given_shared_secret(token, use_command, shared_secret, use_hostname, False, None)
    assert ok

    # ---------- confirm single byte command change breaks verification

    bad_command = use_command.replace('c', 'x')
    ok, status, hostname, username, sent_time = A.validate_token_given_shared_secret(token, bad_command, shared_secret, use_hostname, False, None)
    assert not ok
    assert 'Token fails' in status


# Test the scenario where we're not differenciating between usernames,
# passwords, or even hostnames (the machine specific secret is magically
# transported to the server-side).
def test_puid_only():
    use_command = "mycommand2"

    os.environ['PUID'] = 'mypuid'
    shared_secret = A.generate_shared_secret()
    print('generated client reg: %s' % shared_secret)
    assert len(shared_secret) > 10

    token = A.generate_token_given_shared_secret(use_command, shared_secret)

    ok, status, hostname, username, sent_time = A.validate_token_given_shared_secret(token, use_command, shared_secret)
    print('results: %s, %s, %s, %s, %s' % (ok, status, hostname, username, sent_time))
    assert ok
    assert status == 'ok'
    assert username == ''

    # Regenerate machine registration with same $PUID, make sure it stays the same.
    shared_secret2 = A.generate_shared_secret()
    assert shared_secret == shared_secret2

    # Regenerate machine registration with different $PUID; it should change.
    os.environ['PUID'] = 'differet-puid'
    shared_secret3 = A.generate_shared_secret()
    assert shared_secret != shared_secret3


# Let's confirm the sequence we claim works in the doc..
def test_cli():
    shared_secret = cli(['-g', '-u', 'user1', '-p', 'pass1'])
    assert socket.gethostname() in shared_secret

    out = cli(['-r', shared_secret])
    assert 'Done' in out

    token = cli(['-c', 'command1', '-u', 'user1', '-p', 'pass1'])
    assert token.startswith('v2:')

    out = cli(['-v', token, '-c', 'command1'])
    assert 'validated? True' in out

    os.unlink(A.DEFAULT_DB_FILENAME)
