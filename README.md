# ktools

## About The Project

This is a collection of tools and techniques developed over the last 20
years or so, designed to use and manage a Linux-based home network and
smart-home.  The author's machines are primarily Ubuntu and Raspberry PIs,
although the tools should mostly work on any Debian-derived Linux systems.

These tools represent years of tinkering and fine-tuning, and it is hoped
that this code (even if its only the structural concepts and some of the
specific techniques used) may be of use to those either building their own
systems, or just trying to extend their Linux expertise.

Many Googler engineeringisms are used: from the code formatting style to
the fact that almost everything is a web-server, and the web-servers have
lots of standardized handlers that end with the letter "z' (/logs,
/healthz, /varz, etc.)  Collectively these are referred to as "/z handlers.
However, the author was extremely careful to NOT actually use any Google
intellectual property or trade secrets in the creation of these tools.

## About The Author

Ken Stillson retired from Google's central security team in 2021.  He left
with the rank of "Senior Staff" (level 7 out of 9).  Before that, he worked
at MITRE / Mitretek, assisting the US Government with various
telecommunications and security projects.  He left Mitretek as a "Senior
Principal" (one level shy of "Fellow"), and earned a "Hammer Award" from
the then US Vice President, for work that "makes the government work better
and cost less."

Ken <<ktools@point0.net>> is now a free-range maker, tinkerer, artist, and
hacker (in the good sense).

## About The Structure

These tools were not originally designed to be shared, and made many
assumptions about each other and the environment in which they run.  The
process of disentangling and generalizing them is on-going, and some of the
modules may be initially published in their not-yet-fully-detangled form.
You're welcome to help out via pull requests, or just wait for me to get to
it.

TODO: notes about opinionated dir structure.

The project uses GNU Linux Makefiles.  The code is generally in Python or
bash shell, so doesn't need compilation.  But I likes the way Makefiles
document how things are to be combined, tested, and deployed.

  * "make all" will gather production-ready versions of tools into staging
    areas.  In a few cases, this involves merging in site-specific code or
    data (which aren't included in the git repo due to .gitinclude rules).
    This is how the author hides private or too-specialized-to-be-reusable
    parts of the system.  The idea is that you can insert your own
    site-specific plugins here, if desired.
  
  * "make test" will run whatever unit or integration tests are available.
  
  * "make install" will copy tools from the staging area to final
    destination directories.  The Makefiles are generally written to allow
    environment variables to override the installation directories, so you
    can position the final tools where you like without needing to change
    git controlled files.  For docker-based modules, the "install"
    directive marks the image build by "all" as the currently "live"
    version.  See [docker readme](docker/README.md) for details.
  
  * "make update" is primarily for the author's use.  It runs the above
    sequence in order, then does local git commits, then pulls and pushes
    for all remote repos.

## The Modules

- - -
### DHCP and DNS controls

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

ktools uses a somewhat unusual DHCP and DNS configuration: IP addresses and
hostnames are assigned manually in the DHCP server.  Why?

  1. Security: An new (unregistered) device is immediately noticed and is
  treated differently.
  
  2. Connectivity: Every device has a human-controlled name.  For example,
  in the "tplink" module, it is necessary for the server to be able to
  contact each of the smart plugs/switches/bulbs being controlled.
  
  3. Traceability: Every connection can be traced back to a known
  registered device by IP.  For example, in the "keynmaster" section,
  connection source IP addresses are very important.

It is worth noting that this arrangement requires a flat network.
Specifically, all wireless access points must run in "bridge mode," where
they simply pass traffic back and forth without performing any NAT or IP
masking.  Without this the above benefits are lost and many of the tools
below won't work.

See also the "system-maint" module below, for tools that make DNS assignment and management easy.

- - -

- - -
### homesec: a custom (and highly customizable) home security system framework

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

homesec is essentially a state machine, where various external triggers move it between states, or cause actions depending on the current state.  For example, if the system is in the state "someone is home," then a trigger that an external door has been opened might just ring a chime.   However, a trigger saying "user 1 is leaving" could cause the system to decide no-one remains at home, and enter the "armed" state.  Then that same door trigger would move to "alarm triggered" state, which turns on some lights, sends a cellphone push alert, and speaks an announcement over the home audio system that "alarm triggered, 30 seconds to disarm."  If the system isn't moved to the "disarmed" state within that period, it moves to the "alarm" state, which turns on more lights, pushes more phone messages, and perhaps turns on some annoying sirens.

Triggers are HTTP get requests, with an authentication system based off shared secrets (see the "keymaster" module), and designed to be simple enough so it can run on very small devices, like the Raspberry Pi Zero-w's, which are what generate most of the author's door, window, and motion sensor signals.

homesec is the largest and most complicated of these modules, and will take the longest to detangle and generalize, so it might be a little while before this module gets populated.  It also currently uses Django as a framework, but the author has found Django to be annoying.  Django keeps changing in ways that require continuous re-writing of both user-code and Django integration and settings.  The intention is to replace Django with a simpler and lower-level Python web framework during the detangling. (Flask, perhaps...?)

- - -
### keymaster: solving the digital secret bootstrapping problem

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

It's never a good idea to include plain-text secrets in code.  They're too easy to extract and you have to start being very careful about things like backups.  But automated systems need to talk to each other, and that often needs authentication.  How do these systems get the secrets they'll need, whether these are shared secrets, private keys, or whatever else?

Keymaster ("KM") is a secrets server.  The secrets are stored in an encrypted GPG text file.  When the server starts up, it does not have the key to unlock this data.  An authorized user must access the web-page and provide the GPG passphrase.  KM then decrypts the secrets into local memory.  Clients can then request secrets, but only according to strict rules.  For example, the requestor's source IP address and which key they want must match expectations exactly.  Even a single unexpected request causes the KM to throw away all its decrpyted data and raise an alarm, both signaling that something is very wrong and that a human needs to come provide the decryption password again, once things are safe.

Clients that use KM can start up automatically, but need to be able to gracefully retry for long periods -- long enough for the human to provide the unlock key.  In this way, all services can auto-start, but ones that need secrets won't actually reach their serving state until KM is unlocked.  Unlocking KM is the only manual action a human needs to take upon a network-wide cold-start -- once it's done, all the services waiting on their secrets move to their serving states.

- - -
### nagios: simple nagios CLI interface and enhanced plugins

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

Nagios is a great system for monitoring servers and services, even sizable numbers of them.  It's very easy to customize and extend, and when combined with something like the Android app "aNag," provides a very clean and easy way to keep track of how things are going, and easily silence or acknowledge alerts that one can't respond to immediately.

Included are a cgi-script to provide an extremely simplified status overview, and a CLI tool to query status and request retries.  The CLI tool can also be used as a cgi-script if you want to enable things like remote retry requests for all currently alerting services.

Also included are a few enhanced wrapper-scripts for standard Nagios plugins, and a from-scratch plugin, designed for testing things like the standard "/z handlers" used throughout.

- - -
### rsnapshot: tools and techniques to maximize the value of rsnapshot based backups

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

rsnapshot is a fantastic backup tool- you can keep a variety of daily, weekly, monthly, etc, snapshots.  Rather than using a database to sort out incremental and differential changes, rsnapshot uses file-system hard-links so that each snapshot looks like a complete full backup, but duplicated files are only stored once, regardless of how many times they're duplicated between snapshots.

In the ktools configuration, a central backup server pulls daily updates from many remote servers via rsync-over-ssh.  *However, a root login is not needed to retrieve the data to be backed up.*  A regular account is used, and Linux kernel capabilities are used to give that account the ability to bypass access controls, but for read-only, and only when using rsync.  Further, a restricted shell is assigned to the account, so interactive access to the special uid should be very difficult.

Various examples are provided to guide towards this configuration.

A tool is also provided that generates a filtered list of changes by comparing the last two days' snapshots.  The idea is that one can develop a filter to remove things that are expected change regularly, and receive a daily report of just unusual changes.  This even works with encrypted files- the tool can't decrypt the contents, but it can tell if they've changed.  In this way, should ransomware or anything else corrupt obscure files that you normally wouldn't notice for a while, you'll see a report of unexpected changes and be able to investigate, and preserve the corrupted data in older snapshots before it's rotated out by newer snapshots.

- - -
### syslog-ng: @@ TODO


- - -
### tools: general stand-alone Linux command-line tools

  * iptables_log_sum: summarize rejected packets from iptables logs.
  * ratelimiter: incorporate easy rate-limits into shell scripts
  * run_para: run commands in parallel, showing their real-time output in a dashboard and (optionally) keeping an organized output transcript.

And a special one...

  * q: a collection of Linux shortcuts, tools, and bash tricks.  Hopefully it will eventually be detangeled so the parts that are hopelessly bound with the details of the author's personal configuration can be separated out.  But it's being published anyway. because this script contains considerable wisdom in using and managing a small-to-medium fleet of Linux systems, and contains a repository of bash tips and techniques that provide a good reference for such things.


- - -
### tplink: tools for CLI control of tplink smart lights & plugs, setting complex scenes, etc.

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

The author tends to use TPLink switches, plugs and bulbs for smart-home automation.  Besides having reasonable reliability and cost, TPLink modules have a local server that allow manipulation and querying via local network HTTP.  i.e. you can control them from your own systems without needing to depend on cloud integration.

TPLink has slightly obscured the socket interface, so you can't just use curl or wget.  Python code to work-around this simple xor-based "encryption" is widely available.  What's included here is built on top of that -- a system that allows mapping nice human-readable names to various smart-home actions, and the ability to define arbitrarily complex scenes, including the ability for scenes to reference other scenes, allowing construction of a more modular system.

The "tplink" code can be run directly from CLI, or used as a Python library.  Example cgi-servers are provided that render a bunch of buttons to control individual lights and scenes, and to animate a "party lights" sequence that slowly adjusts the color of RGB bulbs for a festive effect.

