#!/bin/bash

echo ""
echo "testing kmc.sh"
echo ""

out=$(./kmc.sh test test-)
if [[ "$out" != "secret" ]]; then
    echo "FAILED- expected 'secret' and saw '$out'"
    exit 1
fi

echo "ok"
exit 0
