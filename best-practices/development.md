
# General Development Thoughts

## Lots of little pieces

A piece of wisdom inherited from the original Unix design: complex systems
should be built from many pieces, each of which do a single thing, and do that
single thing well.  This applies well to modern systems, and fits perfectly
with the Docker model of micro-services.

From a reliability perspective, the idea is that the many little pieces
represent independent failure domains.  Each little piece should have some
thought put into how to operate in a partial failure mode- i.e. if services it
depends on aren't available, or if confusing commands are received from
services that depend on it.  Services should fight to stay up, and to do the
best they can under partial failure conditions, and of course to report to
monitoring mechanisms that they're having trouble- especially if there's a
chance they are the cause of the trouble.

With all those little pieces trying to keep spinning and trying to right
themselves- when the real underlying problem(s) get fixed, it's amazing how
even quite complex systems experiencing novel failure modes can largely stitch
themselves back together and become healthy again.  This is only possible when
the individual pieces are simple: when their behavior under partial failure is
predictable, and their path to recovery is simple because their fundamental
operation is simple.

From a security perspective, it is much easier to reason about where security
attention needs to go, if the functionality of the unit being secured is easy
enough to fully understand and keep in your head all at once.  An incredible
number of security problems come from two or more features operating as they
were designed, but where some interaction between the features can be
exploited, and this never occurred to the designer(s) because there were too
many features and they were too complex to consider all their interactions.

This pattern isn't perfect.  It is possible for emergent behaviors to
develop, especially in cases where all the individual pieces are simple but
there are so many pieces that their possible interactions are inherently
complex.  It's a bit of an art to design something where both the pieces are
simple and the overall system is simple, and yet the whole thing is still as
capable as it needs to be.  But the goal of having simple pieces is a great
place to start.

btw- I consider Linux "systemd" to be an anti-pattern because of its violation
of this principle.  There were lots of improvements that were needed from the
really old BSD-style init files, but systemd has taken on far far more than
just tidying-up system initialization, and in my opinion has taken a much
larger bite that it can chew.


## Everything should be a web server

Talking to web servers is easy for both humans and machines.  It provides a
reasonably efficient and totally standardized way of both querying data and
issuing commands.  It's trivial when it doesn't need security, and it's not
hard to layer security on-top, including security that's easy for both humans
and automated clients.  It can be routed, tunneled, proxied, and load-balanced
really easily, so you can both enable and disable connectivity to it with a
whole variety of well-known and well-tested tools.

Almost all programs have internal state that can be very valuable to folks
trying to understand and debug them.  It's so much easier to run a few queries
against a status web-page than trying to attach a debugger, or gain access to
and parse your way through endless logs.


## Standard handlers maximize the value of everything being a web server

As you can see in my [kcore/webserver_base](../pylib/kcore/webserver_base.py),
my web server provides a default set of "standard handlers," which allow
querying internal state that the project has deliberately decided to expose
(/varz, /flagz), querying the most recent log messages (/varz), and checking
on system health (/healthz).

The fact that both humans and automated systems can basically rely on those
handlers being available on any systems I've had my fingers on allows
automated health checking and monitoring of operations to be really easy.

At Google there were actually dozens of standard handlers that would come
along with any web server.  Perhaps that was a little over-the-top, but it was
kinda incredible the information one could gather about a piece of software,
its memory use, its threads, its OS, and machine, etc, just by querying
standard handlers.  Anyway, don't be limited by just the standard handlers
I've included.  Put some thought to what else it would be great for you to be
able to easily gather from pretty-much any of your programs, and add a
standard handler for it!
