#!/usr/bin/python3

import os, time

import context_tools     # fix path to includes work as expected in tests
import ratelimiter as R


def test_persistent_file_basics(tmp_path):
    statefile = str(tmp_path / "statefile")

    args = R.parse_args(['--init', '2,1', statefile])
    rl = R.build_instance(args)
    assert os.path.isfile(statefile)
    assert R.do_check(rl, statefile) == True

    args = R.parse_args([statefile])
    rl = R.build_instance(args)
    assert R.do_check(rl, statefile) == True
    assert R.do_check(rl, statefile) == False
    time.sleep(1)
    assert R.do_check(rl, statefile) == True
    assert R.do_check(rl, statefile) == True
    assert R.do_check(rl, statefile) == False

    # Now run in wait mode and make sure it takes at least 1/2 a second.
    now1 = time.time()
    assert R.main(['-w', statefile]) == 0
    now2 = time.time()
    assert now2 - now1 >= 0.5
    assert now2 - now1 < 1.3

