#!/bin/bash

set -e   # stop if there's an error

python3 filewatch_config.py || { echo "error during config syntax check"; exit 1; }

./filewatch.py --config tests/filewatch_config_test.py --test | grep "Overall status: all ok"

echo "pass"
exit 0
