# Monitoring

TODO: reliability vs. security monitoring (see also ID)


## Philosophy

Testing is great- especially automated unit tests which you can run every time
you change something, to give you a reasonably assurance your change works.
But no matter how well you test something, if you just leave it in-place and
expect it work indefinately, you will be disappoined.  Environmental
assumptions and dependncies you didn't even realize you have will change.
Automated systems break down eventually.  *Always.*

So any time you set up something that's supposed to provide a service
indefinately, or run a process regularly- whether automatically or manually,
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
example- I use syslog and ssh-tunnels to centrlize my Linux system log
messages (TODO: link).  Part of my syslog-ng configuration takes messages from
the "cron" and splits them out to separate files based on what host they came
from (TODO: link).  That config is dynamic, i.e. I don't need to manually
register each host with a separate routing rule; when a new host gets wrapped
into the syslog reporting funnel, it gets it's own cron file automatically.

I then use filewatch (TODO: link) to scan all those cron logfiles, and alert
if any of them become more than an hour or so old.  Cron always does
*something* at least every 15 minutes.  So a too-old cron file immediately
tells me something is wrong.  If all the cron logs are too old at the same
time, then most likely something is awry with the centrlized logging system
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

Another useful technique is to deliberate cause change (usually via cron)- for
example, writing random contents to a file (that's what makes it a "cookie").
Then, track the propogation of that random-but-known change as it moves from
place to place throughout your system.  I frequently use this technique to
monitor backup systems.


### /healthz

As noted elsewhere, it's a great idea to make pretty-much-everything a
web-server (TODO: link).  If a program is in a position to know the results of
monitoring, a great way for it to communicate monitoring results is via a web
service.  I follow the Google standard of always having a web path "/healthz".
Querying this path will return the simple 2 character answer "ok" if
everything the program is aware of is fine, and a simple 1-line
human-readaible explanation of what is wrong, if things are not "ok."

It's really easy to design monitoring infrastructure to scan a bunch of web
server /healthz's to see if they're all "ok".


## Monitoring infrastructure: Nagios

I use Nagios as my centrlized monitoring system (TODO: link).  Nagios is
perhaps a bit overengineed for simple use-cases- it supports multiple teams
with dynamic schedules and cascading notifications, etc.  But it's reasonably
easy to skip the complexity when you don't need it.

Basically Nagios tracks a set of hosts (optionally orgnized into "host
groups").  Each host has a set of services, and each service is configured to
use some sort of "check".  The checking system uses a plug-in mechanism that's
quite easy to extend.  Most of the checks reach out to a host and take some
action to "pull" a status update, but there's also support for services
pushing updates when a pull model isn't convenient.

Nagios provides has various status dashboards, although I've written some
simplifed ones that I prefer (TODO: link).  Nagios can also send emails- on
transitions for good-to-bad, and/or bad-to-good, and/or whenever something is
bad, and also supports do-not-disturb times, etc.


## Monitoring infrastructure: aNag

Ok, the famous question- who watches the watcher?  In my case, it's "aNag," an
app for my Android smartphone.  aNag regularly checks in with Nagios, and
triggers a notification on the phone if either Nagios reports a problem, or if
Nagios cannot be contacted or doesn't seem to be updating checks.

aNag also supports per-host or per-service silence requests that auto-expire
after a specified time, and/or can "acknowledge" a problem, which basically
tells Nagios that the necessary humans are working on it, and both Nagios and
aNag should stop perstering.
