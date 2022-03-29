#!/usr/bin/python3

import os, tempfile, time

import context_tools     # fix path to includes work as expected in tests
import ratelimiter


def test_rl_class_nonpersistent():
    rl = ratelimiter.RateLimiter(2.0, 1.0)
    assert rl.check()
    assert rl.check()
    assert not rl.check()
    time.sleep(1)
    assert rl.check()
    assert rl.check()
    assert not rl.check()


def test_persistent_file_basics(tmp_path):
    tempname = str(tmp_path / "out")

    assert ratelimiter.main(['--init', '2,1', tempname]) == 0
    assert os.path.isfile(tempname)

    args = ratelimiter.parse_args([tempname])
    assert ratelimiter.do_check(args) == True
    assert ratelimiter.do_check(args) == True
    assert ratelimiter.do_check(args) == False
    time.sleep(1)
    assert ratelimiter.do_check(args) == True
    assert ratelimiter.do_check(args) == True
    assert ratelimiter.do_check(args) == False

    # Now run in wait mode and make sure it takes at least 1/2 a second.
    now1 = time.time()
    argv = ['-w', '0.2', tempname]
    args_wait = ratelimiter.parse_args(argv)
    ratelimiter.do_check(args_wait)
    ratelimiter.do_check(args_wait)
    assert ratelimiter.do_check(args) == False
    assert ratelimiter.main(argv) == 0
    now2 = time.time()
    assert now2 - now1 >= 0.5
    assert now2 - now1 < 1.3

