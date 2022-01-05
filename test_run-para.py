#!/usr/bin/python3

import os, tempfile

import run_para


# ---------- unit level tests ----------
# (no real tasks launched, direct testing individual lower-level methods)

def test_common_prefix_and_suffix():
    assert run_para.common_prefix_and_suffix(['abcde 12345', 'abcXX 32145', 'abc 345']) == ['abc', '45']
    assert run_para.common_prefix_and_suffix(['abc', 'def']) == ['', '']
    assert run_para.common_prefix_and_suffix(['abc']) == []


def test_gen_id():
    run_para.ARGS = run_para.parse_args([])
    rm = ['abc', '789']
    ids = []
    gen = run_para.gen_id('abcdef6789', ids, rm)
    assert gen == 'def6'
    ids.append(gen)
    gen = run_para.gen_id('abcdef6789', ids, rm)
    assert gen == 'def6.2'
    ids.append(gen)
    gen = run_para.gen_id('abc789', ids, rm)
    assert gen == 'job'
    ids.append(gen)
    gen = run_para.gen_id('abc789', ids, rm)
    assert gen == 'job.2'


def test_process_stdin_auto():
    run_para.ARGS = run_para.parse_args([])
    assert run_para.process_stdin(['a', 'b ', '', 'c']) == ['a', 'b', 'c']
    assert run_para.process_stdin(['a,  , b ,c']) == ['a', 'b', 'c']
    assert run_para.process_stdin(['a  b   c']) == ['a', 'b', 'c']

    
def test_process_stdin_notauto():
    run_para.ARGS = run_para.parse_args(['--sep', ' '])
    assert run_para.process_stdin(['a b  c ']) == ['a', 'b', 'c']
    assert run_para.process_stdin(['a,b c,d ']) == ['a,b', 'c,d']

    run_para.ARGS = run_para.parse_args(['--sep', ','])
    assert run_para.process_stdin(['a b  c ']) == ['a b  c']
    assert run_para.process_stdin(['a,b c,d ']) == ['a', 'b c', 'd']


def test_generate_commands():
    run_para.ARGS = run_para.parse_args([])
    assert run_para.generate_commands(['a', 'b']) == ['a', 'b']

    run_para.ARGS = run_para.parse_args(['--cmd', 'c@d'])
    assert run_para.generate_commands(['a', 'b']) == ['cad', 'cbd']

    run_para.ARGS = run_para.parse_args(['--ssh', 'cmd'])
    assert run_para.generate_commands(['a', 'b']) == ['ssh a "cmd"', 'ssh b "cmd"']

    run_para.ARGS = run_para.parse_args(['--ssh', 'cmd', '--timeout', '10'])
    assert run_para.generate_commands(['a', 'b']) == ['ssh a -o ConnectTimeout=10 "cmd"', 'ssh b -o ConnectTimeout=10 "cmd"']

    
# ---------- integration level tests ----------
# (i.e. actually launch parallel tasks by running run_para.main()

def test_parallel_calcs_with_hinted_ids(tmp_path):
    tempname = str(tmp_path / "out")
    args_test = run_para.parse_args(['--plain', '--output', tempname])
    stdin_list = ['echo ^^1 + 2 | bc',
                  'echo 3 + ^^2 | bc',
                  'echo ^^3 + 4 | bc']
    assert run_para.main(args_test, stdin_list) == 0
    with open(tempname) as f: out = f.readlines()
    assert out[0] == '1: 3\n'
    assert out[1] == '2: 5\n'
    assert out[2] == '3: 7\n'
    assert len(out) == 3


def test_mixed_stdout_and_stderr_and_mixed_return_codes(tmp_path):
    tempname = str(tmp_path / "out")
    args_test = run_para.parse_args(['--plain', '--output', tempname])
    stdin_list = ['echo "^^t1 output1"',
                  'echo "^^t2 error output2" >&2; exit 2',
                  'echo "^^t3 output3"; echo "error3 output" >&2']
    assert run_para.main(args_test, stdin_list) == -1
    # Must sort output, as relative stdout/stderr order not deterministic.
    with open(tempname) as f: out = sorted(f.readlines())
    assert out[0] == 't1: t1 output1\n'
    assert out[1] == 't2: STDERR: t2 error output2\n'
    assert out[2] == 't3: STDERR: error3 output\n'
    assert out[3] == 't3: t3 output3\n'
    assert len(out) == 4


def test_stdin_and_cmd_substitutions(tmp_path):
    tempname = str(tmp_path / "out")
    args_test = run_para.parse_args(['--cmd', 'echo Q', '--plain', '--output', tempname, '--subst', 'Q'])
    stdin_list = ['aa', 'ab', 'ac']
    assert run_para.main(args_test, stdin_list) == 0
    with open(tempname) as f: out = f.readlines()
    # Note that although a is in common to all cmds, common-prefix will 'back up' to
    # the previous space, so it only eliminates 'echo ' not 'echo a'; intended behavior.
    assert out[0] == 'aa: aa\n'
    assert out[1] == 'ab: ab\n'
    assert out[2] == 'ac: ac\n'
    assert len(out) == 3
    

def test_timeouts(tmp_path):
    tempname = str(tmp_path / "out")
    args_test = run_para.parse_args(['--plain', '--output', tempname, '--timeout', '1'])
    stdin_list = ['sleep 0.5; echo "a"',
                  'sleep 1.5; echo "b"']
    assert run_para.main(args_test, stdin_list) == -3
    with open(tempname) as f: out = f.readlines()
    assert out[0] == '0.5; echo a: a\n'
    assert out[1] == '1.5; echo b: TIMEOUT\n'
    assert len(out) == 2

