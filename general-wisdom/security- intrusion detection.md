
# Intrusion Detection: Procmon

[TODO: link]

Intrusion detection (ID) is tricky.  Like all cat-and-mouse games, if one side
knows all the tricks the other side tends to use, then they tend to win.
Alas, most intrusion detection systems are open-source, meaning that hackers
have free access to find them and study their inner workings, whereas the
reverse is not true.

So I tend to advocate for using somewhat bespoke ID mechanisms.  And perhaps
by open-sourcing my own "procmon" solution I'm undermining it's value
somewhat..  But I do try to keep my internal monitoring a little different
from this open-sourced version, and encourage users to do the same.

Anyway, procmon is a process monitor.  At regular intervals, it scans all the
running processes on the system, subtracks out a "whitelist" (apologies for
the no-longer-PC term; I suppose I'll get around to renaming it at some
point), and then alerts on any un-expected remainder.  It also tags some of
the "expected" processes as "required", and alerts if they're missing.

Procmon alerts are "sticky," meaning that even when the unrecognized process
goes away, the alert remains.  It must be manually reset.

Obviously for the first few days of running this, there are going to be a lot
of alerts.  But essentially you just gather them up, convert them into
whitelist entries (after review of course), and it really doesn't take too
long before false-positive alerts are quite rare.

Procmon isn't perfect.  The scanning process is sufficiently expensive that it
only occurs every few minutes.  This means it'll completely miss short lived
processes.  And obviously it doesn't do anything to detect normal-and-expected
processes that have started doing unexpected things.  But still, it brings
reasonable value for very little cost, and can give you a fair bit of comfort
that you have a handle on the set of things running on a server.


## Other functionality

Almost all of my services run in Docker containers.  However, procmon really
needs to see the entire process tree in order to work.  As such, it also
performs a number of other security checks that can only be done outside a
container.

- procmon scans Docker's copy-on-write directories, again subtracting out a
  whitelist of expected files, and alerts on anything that remains.  This
  means that any files that are created or changed in a container that weren't
  expected to do so will immediately be noticed.

- As mentioned in my general linux security notes (TODO: link), I like to keep
  my root file system read-only.  So procmon does a quick check to make sure
  it's write-locked, and alerts if not.


## Alerting

Once a whitelist is sufficiently well-tuned, false positives aren't that
common, but they do happen.  So I always investigate a procmon alert, but I
also don't want to be overly annoyed by them.  So when procmon "raises an
alert," what it's actually doing is changing it's /healthz handler (TODO:
link) to stop indicating that all is well.  This will eventually bubble up
through my normal monitoring system (TODO: link), first showing up as a check
failure in Nagios, and eventually alerting on my phone via aNag.  This gives
me several ways I can temporarily silence an alert (if I want to get to it
later), or "acknowledge" it, which basically makes it go away indefinately.
