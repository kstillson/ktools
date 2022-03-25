
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
    sec = A.generate_client_registration(use_hostname, use_username, use_password)
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

    regblob = A.get_registration_blob(use_hostname, use_username)
    assert regblob is not None
    ok, status, hostname, username, sent_time = A.validate_token_given_registration(token, use_command, regblob, use_hostname, False, None)
    assert ok

    # ---------- confirm single byte command change breaks verification

    bad_command = use_command.replace('c', 'x')
    ok, status, hostname, username, sent_time = A.validate_token_given_registration(token, bad_command, regblob, use_hostname, False, None)
    assert not ok
    assert 'Token fails' in status


# Test the scenario where we're not differenciating between usernames,
# passwords, or even hostnames (the machine specific secret is magically
# transported to the server-side).
def test_puid_only():
    use_command = "mycommand2"

    os.environ['PUID'] = 'mypuid'
    regblob = A.generate_client_registration()
    print('generated client reg: %s' % regblob)
    assert len(regblob) > 10

    token = A.generate_token_given_registration(use_command, regblob)

    ok, status, hostname, username, sent_time = A.validate_token_given_registration(token, use_command, regblob)
    print('results: %s, %s, %s, %s, %s' % (ok, status, hostname, username, sent_time))
    assert ok
    assert status == 'ok'
    assert username == ''

    # Regenerate machine registration with same $PUID, make sure it stays the same.
    regblob2 = A.generate_client_registration()
    assert regblob == regblob2

    # Regenerate machine registration with different $PUID; it should change.
    os.environ['PUID'] = 'differet-puid'
    regblob3 = A.generate_client_registration()
    assert regblob != regblob3


# Let's confirm the sequence we claim works in the doc..
def test_cli():
    regblob = cli(['-g', '-u', 'user1', '-p', 'pass1'])
    assert socket.gethostname() in regblob

    out = cli(['-r', regblob])
    assert 'Done' in out

    token = cli(['-c', 'command1', '-u', 'user1', '-p', 'pass1'])
    assert token.startswith('v2:')

    out = cli(['-v', token, '-c', 'command1'])
    assert 'validated? True' in out

    os.unlink(A.DEFAULT_DB_FILENAME)
