
# Monitoring

Monitoring is critical for both reliability and intrusion detection.  This
document is about the former see [this doc](security-intrusion_detection.md)
for the latter.


## Philosophy

Testing is great- especially automated unit tests which you can run every time
you change something, to give you a reasonably assurance your change works.
But no matter how well you test something, if you just leave it in-place and
expect it work indefinitely, you will be disappointed.  Environmental
assumptions and dependencies you didn't even realize you have will change.
Automated systems break down eventually.  *Always.*

So any time you set up something that's supposed to provide a service
indefinitely, or run a process regularly- whether automatically or manually,
you should also design and implement a way to monitor it.


With unit tests, the goal is usually to have small tests that are very tightly
bound to the code they are testing.  In this way, when a test breaks, it's
usually quite easy to identify the part of the code responsible.  You can take
that approach with monitoring, but I often find it's not worth it.  Monitoring
can often be done more easily at a higher level- determining whether some
larger sequence of processes is having the right end results.  As a
consequence, a monitoring alert doesn't necessarily tell you exactly what is
wrong, but rather brings to your attention that *something* is wrong, and gets
you started running more specific tests to figure out what.


## Techniques

### Timestamps

One of my favorite things to monitor is file last-change timestamps.  As an
example- I use syslog and ssh-tunnels to centralize my Linux system log
messages.  Part of my [syslog-ng
configuration](../containers/syslogdock/files/etc/syslog-ng/syslog-ng.conf)
takes messages from "cron" and splits them out to separate files based on what
host they came from.  That config uses a glob expression, i.e. I don't need to
manually register each host with a separate routing rule; when a new host gets
wrapped into the syslog reporting funnel, it gets it's own cron file
automatically.

I then use [filewatch](../services/filewatch) to scan all those cron log files,
and alert if any of them become more than an hour or so old.  Cron always does
*something* at least every 15 minutes.  So a too-old cron file immediately
tells me something is wrong.  If all the cron logs are too old at the same
time, then most likely something is awry with the centralized logging system
(or filewatch).  If it's just one or two machines, it might be a system-wise
problem on those machines, or just their logging system, or ssh tunnels, etc.
But the filename of the too-old log tells me the machine(s) to look at, and
immediately I'm well underway in diagnosing the problem.


### Automated monitoring of manual processes

Sometimes manual processes are necessary- plugging in storage mediums, etc.
Even diligent humans can get distracted and forget to do things they're
usually very reliable about.

File change stamps work great for making sure that manual processes are being
executed on schedule.  Just make sure that the manual process involves running
a script, pressing a button, or such.  And have that manual action modify a
tracking file.  Then monitor the file for an expected change window.


### Change cookies

Another useful technique is to deliberately cause change (usually via cron)-
for example, writing random contents to a file (that's what makes it a
"cookie").  Then, track the propagation of that random-but-known change as it
moves from place to place throughout your system.  I frequently use this
technique to monitor backup systems:  I copy a change-cookie into the backup
system, then copy it back to a different location and compare the two.  If
they're different, something in the backup system isn't working.


### /healthz

As noted elsewhere, it's a great idea to [make pretty-much-everything a
web-server](development.md).  If a program is in a position to know the
results of its own status or the monitoring of other systems' statuses, a
great way for it to communicate monitoring results is via a web page.  I
follow the Google standard of always having a web path "/healthz".  Querying
this path will return the simple 2 character answer "ok" if everything the
program is aware of is fine, and a simple 1-line human-readable explanation of
what is wrong, if things are not "ok."

It's really easy to design monitoring infrastructure to scan a bunch of web
server /healthz's to see if they're all "ok".  Here's my [Nagios
plugin](../containers/nagdock/files/usr/lib/nagios/plugins/check_healthz)
to make this really easy.


## Monitoring infrastructure: Nagios

I use Nagios as my [centralized monitoring
system](../containers/nagdock).  Nagios is perhaps a bit
over-engineered for simple use-cases- it supports multiple teams with dynamic
schedules and cascading notifications, etc.  But it's reasonably easy to skip
the complexity when you don't need it.

Basically Nagios tracks a set of hosts (optionally organized into "host
groups").  Each host has a set of services, and each service is configured to
use some sort of "check".  The checking system uses a plug-in mechanism that's
quite easy to extend.  Most of the checks reach out to a host and take some
action to "pull" a status update, but there's also support for services
pushing updates when a pull model isn't convenient.

Nagios provides has various status dashboards, although I've written some
[simplified ones that I prefer](../pylib/tools/nag.py).  Nagios can also send
emails- on transitions for good-to-bad, and/or bad-to-good, and/or whenever
something is bad, and also supports do-not-disturb times, etc.


## Monitoring infrastructure: monitoring Nagios

Ok, the famous question- who watches the watcher?

I used to use the Android app "aNag," although it's been having problems
recently.  So I implemented my own simple replacement using the Android Tasker
app.  You can find the source code [here](../tools-etc/Tasker/Nagger.prj.xml)


## Monitoring infrastructure: [syslog-ng][syslog-ng]

Finally, let's talk about Linux system logs.  Linux generates *a lot* of
system logs, and it can be difficult to pick out the interesting ones.

Over time, I've developed a pretty good [configuration for
syslog-ng](../containers/syslogdock/files/etc/syslog-ng/syslog-ng.conf).

Here's the idea -- I divvy log messages into one a several categories:

1. Things I know to be critically important.
1. Things I know to be moderately important.
1. Things I know to be "routine".
1. Things I know to be completely unimportant.
1. Things I don't know how to categorize.


### cat 1: Critical things: immediate email

For the most important things (filter "f\_crit"), I sent them immediately to
myself via email (destination "d\_email"), and also add them to "the queue"
(d\_queue), see the next section for details.


### cat 2: Moderately important things: the queue

I think of the queue as things that don't need immediate attention, but do
need attention at some point- i.e. within a day or so..  So items in this
"moderately important" category get thrown in a file (/var/log/queue), and
each night, a logrotate script mails me the contents of that file, and clears
it.

In the morning I look through my queue, with the goal of doing *something*
about each log entry mailed to me.  Whether that's creating a rule to route
them to some other log category, or fixing whatever went wrong- anything in
the queue is an action item for me to deal with, and I don't delete the queue
notification email until it's done (which bugs the heck out of me, as I try
hard to maintain
[Inbox Zero](https://www.techtarget.com/whatis/definition/inbox-zero).

Actually, in truth I have 3 separate queues.  d\_queue, d\_error, and
d\_bashlog.  The error queue is things that came in with the log level of
"error" (or higher) and which were not filtered into one of the other
categories.  I separate it from d\_queue just to help keep things organized.

As for the bashlog- I have a few systems where it's very unusual for me to
need to log into an interactive bash shell, especially as root.  So I use a
modified shell that sends every entered command to syslog.  And then those
syslog entries get sent to d\_bashlog.  As with the other queues, this file is
mailed to me nightly and simultaneously cleared.  In the morning, I glance at
the bashlog mail, just enough to confirm that it was indeed me, and that those
are at least approximately the commands I remember entering.


### cat 3: routine/default: store with forensics in mind

For things that represent routine operations, I keep these things around for a
few weeks, just in-case they end up being useful for a forensic investigation.
i.e. if I end up suspecting an intrusion, log messages can be very helpful for
tracking what/when the intruder did.  I separate these messages into different
log files based usually on what program/service generated them, or however
else I think will organize the messages such that things are grouped together
sensibly should I end up doing an investigation.

This whole collection of "routine" log messages is automatically swept away by
logrotate, after a suitable "so long ago I really don't care anymore" period.


### cat 4: junk: short term storage

By far my largest and most complicated filtering rule is f\_junk, which picks
out messages that I'm reasonably confident have no forensic or other value,
and are really just cluttering up the logs with useless junk.  All these
messages are mushed together into one big d\_junk file, which I do still keep
around for a few days, but which is generally rotated out much more quickly
than the other categories.


### cat 5: everything else: queue

**This is the real kicker for the system- what makes it valuable.**

Any incoming log message that isn't specifically routed to one of the 'I know
what to do with this categories' above, gets sent to the same queue as my
moderately important messages: the queue.

Recall that each log message that lands in the queue is an assignment to me,
do to something about that message.  98% of the "I've never seen that before"
messages end up getting a new routing rule that sends them to junk or to
routine operations.

But that 2%..  That's an incredibly important 2%.  Those are the log messages
that represent an actually interesting situation.  I don't have a rule to
categorize the message because the thing that triggered it hasn't happened
before.  And, if it's a member of the precious 2%, it's a novel situation that
I actually need to know about.

The goal of course, is to have so few messages land in the queue that when one
does, it's reliably something you really need to know about.  It takes a while
to develop sufficiently broad category 3 and 4 filters that this is true.  But
once it is -- you've reached a system logging nirvana.  Novel situations are
brought to your attention, while routine ones are automatically stored away in
an organized fashion, just in-case you need them.

