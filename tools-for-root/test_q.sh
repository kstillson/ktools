#!/bin/bash

# This is not currently a real test-suite.  It basically just sanity checks
# a few of the self-introspection capabilities of q.sh, basically showing
# that it's able to run and the self-inspection basically works.
#
# TODO: a proper test suite for q.sh would take a while, but be valuable.

TARGET="./q.sh"
function die() { echo "ERROR: $@" >&2; exit -1; }

# --------------------

num_commands=$(${TARGET} commands | wc -l)
if [[ "$num_commands" -lt 10 ]]; then die "too few commands in self-eval: $num_commands"; fi
if [[ "$num_commands" -gt 300 ]]; then die "too many commands in self-eval: $num_commands"; fi
echo "self-eval number of commands ok: $num_commands"

dup_chk=$(${TARGET} dup-check)
if [[ "$dup_chk" != "all ok" ]]; then die "internal duplicate check command failed: $dup_chk"; fi
echo "duplicate check ok"

# --------------------

echo "all ok"
exit 0
