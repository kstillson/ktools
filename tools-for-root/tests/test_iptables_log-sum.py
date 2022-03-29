#!/usr/bin/python3

import context_tfr     # fix path to includes work as expected in tests

import iptables_log_sum as base

def test1():
    counter = base.generate_counter(['testdata/iptables-1.testlog'], '++', 9999)
    assert(len(counter.counter)) == 2
    for key, count in counter.counter.items():
        if ' log-drop-fwd:' in key: expect = 1
        elif '  a1-log-drop-in:' in key: expect = 6
        else: expect = -1
        assert expect == count

