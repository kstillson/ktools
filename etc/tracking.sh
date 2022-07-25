#!/bin/bash

# As mentioned in the top-level README.md file, this system has a simple and
# primitive tracking system.  It's here because (a) I wouldn't mind having
# some information on the folks using it [and not paying enough attention to
# disable it], but more importantly, (b) to serve as an educational reminder
# that software downloaded off the Internet is risky..  It can have all sorts
# of things in there you didn't expect.
#
# In this case, all you have to do is set the environment variable NO_TRACKING
# to anything non-blank, and assuming that I haven't sneakily added any other
# more subtle tracking mechanisms that don't respect $NO_TRACKING (which of
# course I might have), then you're all good to go.

if [[ -n "$NO_TRACKING" ]]; then exit 0; fi

wget -q -O- -t2 -T3 -w2 "https://point0.net/tracking?sys=ktools&ctx=$1&uid=${UID}"

exit 0
