#!/bin/bash

set -e   # stop if there's an error

python3 procmon_whitelist.py || { echo "error during whitelist syntax check"; exit 1; }

./procmon.py --logfile - --nocow --nodmap --noro --output '' --queue '' --test --whitelist tests/procmon_whitelist_test.py |& fgrep -v Skipping | tee /dev/stderr | grep "all ok"

echo "pass"
exit 0
