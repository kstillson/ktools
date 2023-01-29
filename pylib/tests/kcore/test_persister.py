
import context_kcore   # fixup Python include path

import os, time
from dataclasses import dataclass

import kcore.persister as P


# TODO(defer): add locking based tests


@dataclass
class Dc1:
    f1: str
    f2: int

@dataclass
class Dc2:
    f2: int
    f1: str
    f3: str = 'f3-default'


# ---------- baseclass Persister

def test_persister_atomic_types(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.Persister(tempfile)
    d2 = P.Persister(tempfile)

    d1.set_data(14)
    assert d2.get_data() == 14

    time.sleep(0.1)  # Ensure enough time passes to see timestamps as different.
    d1.set_data('hithere')
    assert d1.get_data() == 'hithere'
    assert d2.get_data() == 'hithere'


def test_persister_simple_list(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.Persister(tempfile)
    d2 = P.Persister(tempfile)

    d1.set_data([1, 2, 3])
    assert d2.get_data() == [1, 2, 3]

    time.sleep(0.1)  # Ensure enough time passes to see timestamps as different.
    with d1.get_rw() as d: d[1] = 99
    with d2.get_ro() as d: assert d[1] == 99


def test_persister_simple_list_with_default(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.Persister(tempfile, default_value=[])
    d2 = P.Persister(tempfile)

    with d1.get_rw() as d:
        d.append(11)
    assert d2.get_data()[0] == 11


def test_persister_simple_list_get_rw_with_default(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.Persister(tempfile, default_value=[])
    d2 = P.Persister(tempfile)

    with d1.get_rw() as d: d.append(11)
    assert d2.get_data()[0] == 11


def test_persister_simple_dict(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.Persister(tempfile)
    d2 = P.Persister(tempfile)

    d1.set_data({'k1': 'v1', 'k2': 'X'})
    with d1.get_rw() as d:
        d['k2'] = 'v2'

    assert d2.get_data()['k2'] == 'v2'


# ---------- a single dataclass

def test_persister_single_dc(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.PersisterDC(tempfile, Dc1)
    d2 = P.PersisterDC(tempfile, Dc1)

    x = Dc1('hi', 27)
    d1.set_data(x)
    assert d2.get_data().f2 == 27

    time.sleep(0.1)  # Ensure enough time passes to see timestamps as different.
    with d1.get_rw() as d: d.f2 = 28
    assert d2.get_data().f2 == 28


def test_single_dc_tolerant_deserialization():
    p = P.PersisterDC(None, Dc2)
    s = '''# comment that looks like = assignment
  ; indented comment
 junk line with no equals sign.
f3 = val3   # unquoted string and trailing comment with spaces before it

  f2= 12  ; another trailing comment
f1=   ' quoted with internal # and leading and trailing spaces '  # and a trailing comment  '''

    d = p.deserialize(s)
    assert d.f1 == ' quoted with internal # and leading and trailing spaces '
    assert d.f2 == 12
    assert d.f3 == 'val3'


def test_single_dc_invalid_field():
    p = P.PersisterDC(None, Dc2)
    s = 'invalid_field = hithere'
    try:
        d = p.deserialize(s)
        assert '' == 'expected ValueError :-('
    except ValueError as e:
        assert '"invalid_field" not defined' in str(e)


# ---------- dict of dataclasses

def test_dict_of_dataclasses(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.PersisterDictOfDC(filename=tempfile, rhs_type=Dc1)
    d2 = P.PersisterDictOfDC(tempfile, Dc1)

    with d1.get_rw() as d:
        d['key1'] = Dc1('str1', 11)
        d['key2'] = Dc1('str2', 22)
        d['key3'] = Dc1('str3', 33)

    with d2.get_ro() as d:
        assert d['key2'].f2 == 22

    snapshot = d2.get_data()
    assert snapshot['key3'].f2 == 33

    time.sleep(0.1)  # Ensure enough time passes to see timestamps as different.
    with d1.get_rw() as d:
        d['key2'].f2 = 99

    assert snapshot['key2'].f2 == 22
    assert d1.get_data()['key2'].f2 == 99
    assert d2.get_data()['key2'].f2 == 99

    # Check that serialized format is human-readable, as expected.
    with open(tempfile) as f: serialized = f.read()
    lines = serialized.split('\n')
    assert lines[0] == "'key1': Dc1(f1='str1', f2=11)"
    assert lines[1] == "'key2': Dc1(f1='str2', f2=99)"


def test_dict_of_dataclasses_with_serialized_tabs(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.PersisterDictOfDC(tempfile, rhs_type=Dc1)
    with open(tempfile, 'w') as f:
        f.write("'key3':\tDc1(f1='str3', f2=11)\n'key4': \t \t Dc1(f1='str4', f2=123)\n")

    d = d1.get_data()
    assert d['key3'].f1 == 'str3'
    assert d['key4'].f2 == 123
    assert len(d) == 2


# ---------- list of dataclasses

def test_list_of_dataclasses(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.PersisterListOfDC(tempfile, Dc1)
    d2 = P.PersisterListOfDC(tempfile, Dc1)

    with d1.get_rw() as d:
        d.append(Dc1('str1', 11))
        d.extend([Dc1('str2', 22), Dc1('str3', 33)])

    with d2.get_ro() as d:
        assert len(d) == 3
        assert d[1].f2 == 22

    snapshot = d2.get_data()
    assert snapshot[2].f2 == 33

    time.sleep(0.1)  # Ensure enough time passes to tell there's been an update.
    with d1.get_rw() as d:
        d[1].f2 = 99

    assert snapshot[1].f2 == 22
    assert d1.get_data()[1].f2 == 99
    assert d2.get_data()[1].f2 == 99

    # Check that serialized format is human-readable, as expected.
    with open(tempfile) as f: serialized = f.read()
    lines = serialized.split('\n')
    assert lines[0] == "Dc1(f1='str1', f2=11)"
    assert lines[1] == "Dc1(f1='str2', f2=99)"


# ----- convenience classes

def test_DictOfDataclasses(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.DictOfDataclasses(filename=None, rhs_type=Dc1)  # Filename deferred.
    d2 = P.DictOfDataclasses(None, Dc1)

    with d1.get_rw():
        d1.filename = tempfile
        d1['key1'] = Dc1('strA', 111)
        d1['key2'] = Dc1('strB', 222)

    d2.filename = tempfile
    assert d2.get_data()['key2'].f2 == 222


def test_ListOfDataclasses(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    d1 = P.ListOfDataclasses(tempfile, Dc1)
    d2 = P.ListOfDataclasses(tempfile, Dc1)

    with d1.get_rw() as d:
        d.append(Dc1('strC', 33))
        d.append(Dc1('strD', 44))

    assert len(d2) == 0                # get_data() not called yet.
    assert d2.get_data()[1].f2 == 44


# ---------- with encryption

def test_encryption_addin(tmp_path):
    tempfile = str(tmp_path / "tempfile")
    password = 'this-is-very-secret'

    d1 = P.Persister(tempfile, password=password)
    d2 = P.Persister(tempfile, password=password)

    d1.set_data(1337)
    assert d2.get_data() == 1337

    with open(tempfile) as f: encrpyted = f.read()
    assert encrpyted.startswith('pcrypt1:')

    try:
        d3 = P.Persister(tempfile, password='incorrect-password')
        assert '' == 'fail: expected exception'
    except ValueError as e:
        assert 'invalid password' in str(e)
