#!/usr/bin/python3

import iptables_log_sum as base

def test1():
    counter = base.generate_counter(['testdata/iptables-1.log'], '++', 9999)
    print(f'@@ c={counter.counter}')
    assert(len(counter.counter)) == 2
    for key, count in counter.counter.items():
        if ' log-drop-fwd:' in key: expect = 1
        elif '  a1-log-drop-in:' in key: expect = 6
        else: expect = -1
        assert expect == count

def test_fail():
    assert 1 == 2

