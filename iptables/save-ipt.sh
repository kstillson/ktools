#!/bin/bash

# TODO: replace this with a script that uses the standard location, but
# automatically remounts root writable if needed.

/bin/mv -f ~/iptables.rules ~/iptables.rules.prev
/usr/sbin/iptables-save > ~/iptables.rules
echo "saved"
exit 0
