
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
        assert expected_keyname in secrets
        assert secrets.get(expected_keyname).secret == expected_secret
    assert len(ref_dict) == len(secrets)
    return secrets


# ---------- tests

def test_basics(tmp_path):
    secrets_file = str(tmp_path / 'secrets-db.gpg')
    stnd_args = ['--datafile', secrets_file,
                 '--password', PASSWORD]

    # generate test key and check it

    with UC.Capture() as cap:
        assert K.main(['--testkey']) == 0
        testkey = cap.out
        assert cap.err == ''
    assert 'PGP MESSAGE' in testkey
    with open(secrets_file, 'w') as f: f.write(testkey)
    check_db(secrets_file, {'testkey': 'mysecret'})

    # add a key

    assert K.main(stnd_args + ['--acl', '@*', '--keyname', 'key1', '--secret', 'secret1']) == 0
    check_db(secrets_file, {'testkey': 'mysecret', 'key1': 'secret1'})

    # try changing that key without --force

    try:
        K.main(stnd_args + ['--keyname', 'key1', '--secret', 'secret1b'])
        assert 'was expecting a failure.' == ''
    except SystemExit as e:
        assert 'already exists' in str(e)
    check_db(secrets_file, {'testkey': 'mysecret', 'key1': 'secret1'})

    # try changing that key with --force

    assert K.main(stnd_args + ['--keyname', 'key1', '--secret', 'secret1c', '--force']) == 0
    check_db(secrets_file, {'testkey': 'mysecret', 'key1': 'secret1c'})

    # and try removing that key

    assert K.main(stnd_args + ['--remove', '--keyname', 'key1']) == 0
    check_db(secrets_file, {'testkey': 'mysecret'})
