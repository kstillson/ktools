
import sys

import kcore.uncommon as UC

import context_km_svc     # fix path to includes work as expected in tests
import km_helper as K
from km import Secret, Secrets

PASSWORD = 'test123'


# ---------- helpers

def check_db(filename, ref_dict):
    secrets = Secrets()
    secrets.load_from_gpg_file(filename, PASSWORD)
    for expected_keyname, expected_secret in ref_dict.items():
        assert secrets.get(expected_keyname).secret == expected_secret
    assert len(ref_dict) == len(secrets)
    return secrets


# ---------- tests

def test_basics(tmp_path):
    key_file = str(tmp_path / 'key-db.gpg')
    puid_file = str(tmp_path / 'puid-db.gpg')
    stnd_args = ['--datafile', key_file,
                 '--puid-db', puid_file,
                 '--password', PASSWORD,
                 '--hostname', 'host1']

    # generate test key and check it

    with UC.Capture() as cap:
        assert K.main(['--testkey']) == 0
        testkey = cap.out
        assert cap.err == ''
    assert 'PGP MESSAGE' in testkey
    with open(key_file, 'w') as f: f.write(testkey)
    check_db(key_file, {'*-testkey': 'mysecret'})

    # add a puid to the puid-db

    assert K.main(stnd_args + ['--register-puid', '--puid', 'puid1']) == 0

    # add a key using that puid

    assert K.main(stnd_args + ['--keyname', 'key1', '--secret', 'secret1']) == 0
    check_db(key_file, {'*-testkey': 'mysecret', 'host1-key1': 'secret1'})

    # try changing that key without --force

    try:
        K.main(stnd_args + ['--keyname', 'key1', '--secret', 'secret1b'])
        assert 'was expecting a failure.' == ''
    except SystemExit as e:
        assert 'already exists' in str(e)
    check_db(key_file, {'*-testkey': 'mysecret', 'host1-key1': 'secret1'})

    # try changing that key with --force

    assert K.main(stnd_args + ['--keyname', 'key1', '--secret', 'secret1c', '--force']) == 0
    check_db(key_file, {'*-testkey': 'mysecret', 'host1-key1': 'secret1c'})

    # and try removing that key

    assert K.main(stnd_args + ['--remove', '--keyname', 'host1-key1']) == 0
    check_db(key_file, {'*-testkey': 'mysecret'})
