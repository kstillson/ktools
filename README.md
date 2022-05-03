# ktools

## About The Project

This is a collection of services, tools, and libraries, intended for
moderately knowledable owners of Linux and Circuit-Python based systems.

Some highlights:

- A smart-home control system

- A home security system (integrated with the smart-home system)

- A collection of scripts and Docker containers designed to provide
  security-focused services, monitoring, and administrative automation for a
  home-network of Linux servers (bigs ones and little ones like Raspberry PIs)

- Docker infrastructure for quick and easy maintence of the provided
  containers, and simple addition of new ones

- A Python library that underpins all of the above, providing:

   - A mechanism that provides authentication and automated secret retrieval
     without needing to store private keys or other secrets in plaintext on
     either the server or the clients.

   - A very simple to use logging abstraction that integrates level filtering
     for various outputs (files, stdout, stderr, syslog), as well a web-based
     log retrieval.

   - A web server and client designed for simplicity of use, and which also
     provides a uniform interface for a number of platforms: Python 2 or 3,
     Raspberry PI, and Circuit Python.  Also includes a bunch of
     Google-engineering-inspired "standard handlers" that make remote
     monitoring and debugging easier.

   - A GPIO and Neopixel abstraction that works on full Linux, Raspberry PIs,
     and Circuit Python boards.  Under full Linux, the GPIOs and Neopixels are
     simulated (graphically).  This means you can develop on a full Linux
     machine with PDB and all the other nicities, and upload the code to RPi
     or Circuit Python once it's almost done.

The collection represent years of tinkering and fine-tuning, and it is hoped
that this code, even if only the structural concepts and some of the
techniques, may be of use to those either building their own systems, or just
trying to extend their Linux or Python expertise.


## About The Author

Ken Stillson retired from Google's central security team in 2021.  He left
with the rank of "Senior Staff" (level 7 out of 9).  Before that, he worked at
MITRE / Mitretek, assisting the US Government with various telecommunications
and security projects.  He left Mitretek as a "Senior Principal" (one level
shy of "Fellow"), and earned a "Hammer Award" from the then US Vice President,
for work that "makes the government work better and cost less."

Ken <<ktools@point0.net>> is now a free-range maker, tinkerer, artist, and
hacker (in the good sense).


## About the Status

These tools were not originally designed to be shared, and made many
assumptions about each other and the environment in which they run.  The
process of disentangling and generalizing them is on-going, and some of the
modules are being published in their not-fully-detangled form.  You're welcome
to help out via pull requests, or just wait for me to get to it.

As an example, much of teh system current has various assumptions about
directory structures.  Most Debian/Ubuntu users won't find my directory
choices disturbing, but usually open-source projects allow users to choose
where things should be installed.  It turns out that refitting a complicated
system with many hard-coded directory assumptions is challenging.


## Makefile's

The project uses GNU Linux Makefile's.  A bit old fashioned, I know.  And the
code is generally in Python or bash, i.e. no compilation phase, which might
make "Make" seem like an odd choice.  However, I like the way Makefile's
document dependencies and how things are to be combined, tested, and deployed.
Even when an overall process becomes complicated, well-writen Makefile's
remain small and reasonably easy to understand.

  * "make prep" is a custom rule I added, which does some one-time prepratory
    stuff, like making sure various dependencies are installed, and getting
    information from you for populating the self-signed certificates used by
    the authentication system.

  * "make all" despite being the default make target, the top-level Makefile
    "all" doesn't actually do anything except depend on "prep".  This is
    because Python and Bash scripts don't need compiling.

    The "all" target does build Docker containers when run in docker-container
    subdirs, but I decided not to have the top level Makefile automatically
    build the containers, as doing so has additional prerequisites (such as
    installing Docker and running as root), and I figured users might be
    alarmed if a top level "make all" started sudo'ing (which isn't common
    practice).  If you do want to build Docker containers, run "make all"
    either in a specific container's directory
    (e.g. docker-containers/kcore-baseline), or in the ./docker-containers
    diretory to build them all, or see the "make everything" target (below).
  
  * "make test" runs unit and/or integration tests.  For servers and Docker
    containers, this involves actually starting the systems up and peppering
    them with tests to confirm operation.
  
  * "make install"- for libaries and services, copies files into their
    appropriate bin/ or lib/ directories.  For docker containers, tags
    the ":latest" image as ":live", which will cause it to be used
    the next time the container is restarted.

  * "make update" basically runs "all" then "test" then "install"

  * "make everything" This target is only in the top-level Makefile.  It
    basically runs "make update" for everything, including all the Docker
    containers.  It's also aware of the order dependencies for Docker builds,
    specifically- that "kcore-baseline" container must be build *and
    installed* (which just means tagging the image as "live") before the other
    containers are built.  This is because the other containers use
    "kcore-baseline" as their image starting point.


### Makefile Errata

TODO: all the below stuff will eventually be fixed..

- At the moment, the various different subdirectory's Makefile's aren't as
  uniform as they should be in terms of which targets do what.  For example,
  some "install" targets automatically use sudo because they need root privs
  to do their work.  Some automatically detect the current user-id, and
  perform a system-wide installation for root and a personal installation
  otherwise, and some detect the user-id, but if run as non-root will mention
  that a system-wide installation is needed for other parts of the overall
  system to work, and will interactively ask if they should sudo and repeat
  the install system-wide.  (It's unusual and unexpected for a Makefile to
  interact with the user directly.)

- In addition, a few of the "update" targets automatically restart a service
  or container as part of the process, but not all of them.  This needs to
  be made uniform and predictable.  Perhaps an environment variable to
  toggle the behaviour...?

- Several of the Makefile's have other custom targets, especially the one for
  "pylib", which has various options such as "install-wheel" (to use the pip3
  based "wheel" based installation process), or "install-simple" to install
  via simple copies (using "best guess" to figure out target directories), and
  also has an "install-system" to do a wheel-based install, but into the
  system-wide /usr/local rather than the personal ~/.local directory.


If you're not interested in digging into the Makefile's to understand all
these details, you can always use the top-level "make everything" target.  It
does everything, and all in the correct order, and don't require you to
understand any of these subtleties.

- - -

# Contents

## general-wisdom

The first thing I'd like to call attention to is the "general-wisdom"
subdirectory.  This directory contains several decades of system
administration and programming experience, distilled down to a few kilobytes.

For example, it describes my backup strategy- what threats I'm trying to be
ready for, how I construct my unified solution, and provides links to the
various implementation pieces throughout the other directories.

There's also a bunch of thoughts on security- not just the background and
philosophy for the modules provided here, but also more general approaches and
recommendations for passwords, encryption, using browsers safely, etc.  I'd be
willing to bet there are very few people in the world who have already thought
of all the things included here.

Finally, my design schemes for Linux system administration are laid out.
Basically this is an explanation and road-map for the remaining services and
Docker images.  You can certainly use these things without reading the docs,
but chances are you'll end up missing out on some of the key benefits of
things like running your own DHCP and DNS services, if you don't understand
how I use DHCP configuration to create pseudo subnets with different levels of
trust.

- - -

@@

## homesec: a custom (and highly customizable) home security system framework

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

homesec is essentially a state machine, where various external triggers move
it between states, or cause actions depending on the current state.  For
example, if the system is in the state "someone is home," then a trigger that
an external door has been opened might just ring a chime.  However, a trigger
saying "user 1 is leaving" could cause the system to decide no-one remains at
home, and enter the "armed" state.  Then that same door trigger would move to
"alarm triggered" state, which turns on some lights, sends a cellphone push
alert, and speaks an announcement over the home audio system that "alarm
triggered, 30 seconds to disarm."  If the system isn't moved to the "disarmed"
state within that period, it moves to the "alarm" state, which turns on more
lights, pushes more phone messages, and perhaps turns on some annoying sirens.

Triggers are HTTP get requests, with an authentication system based off shared
secrets (see the "keymaster" module), and designed to be simple enough so it
can run on very small devices, like the Raspberry Pi Zero-w's, which are what
generate most of the author's door, window, and motion sensor signals.

homesec is the largest and most complicated of these modules, and will take
the longest to detangle and generalize, so it might be a little while before
this module gets populated.  It also currently uses Django as a framework, but
the author has found Django to be annoying.  Django keeps changing in ways
that require continuous re-writing of both user-code and Django integration
and settings.  The intention is to replace Django with a simpler and
lower-level Python web framework during the detangling. (Flask, perhaps...?)

- - -

## keymaster: solving the digital secret bootstrapping problem

It's never a good idea to include plain-text secrets in code.  They're too
easy to extract and you have to start being very careful about things like
backups.  But automated systems need to talk to each other, and that often
needs authentication.  How do these systems get the secrets they'll need,
whether these are shared secrets, private keys, or whatever else?

Keymaster ("KM") is a secrets server.  The secrets are stored in an encrypted
GPG text file.  When the server starts up, it does not have the key to unlock
this data.  An authorized user must access the web-page and provide the GPG
passphrase.  KM then decrypts the secrets into local memory.  Clients can then
request secrets, but only according to strict rules.  For example, the
requestor's source IP address and which key they want must match expectations
exactly.  Even a single unexpected request causes the KM to throw away all its
decrpyted data and raise an alarm, both signaling that something is very wrong
and that a human needs to come provide the decryption password again, once
things are safe.

Clients that use KM can start up automatically, but need to be able to
gracefully retry for long periods -- long enough for the human to provide the
unlock key.  In this way, all services can auto-start, but ones that need
secrets won't actually reach their serving state until KM is unlocked.
Unlocking KM is the only manual action a human needs to take upon a
network-wide cold-start -- once it's done, all the services waiting on their
secrets move to their serving states.

- - -

## tools: general stand-alone Linux command-line tools

  * iptables_log_sum: summarize rejected packets from iptables logs.

  * ratelimiter: incorporate easy rate-limits into shell scripts

  * run_para: run commands in parallel, showing their real-time output in a
    dashboard and (optionally) keeping an organized output transcript.

And a special one...

  * q: a collection of Linux shortcuts, tools, and bash tricks.  Hopefully it
    will eventually be detangeled so the parts that are hopelessly bound with
    the details of the author's personal configuration can be separated out.
    But it's being published anyway. because this script contains considerable
    wisdom in using and managing a small-to-medium fleet of Linux systems, and
    contains a repository of bash tips and techniques that provide a good
    reference for such things.

- - -

## home-control: tools for CLI control of tplink smart lights & plugs, setting
   complex scenes, etc.

<p style="color:purple"><b>not included yet: still being prepared for publication...</b></p>

The author tends to use TPLink switches, plugs and bulbs for smart-home
automation.  Besides having reasonable reliability and cost, TPLink modules
have a local server that allow manipulation and querying via local network
HTTP.  i.e. you can control them from your own systems without needing to
depend on cloud integration.

TPLink has slightly obscured the socket interface, so you can't just use curl
or wget.  Python code to work-around this simple xor-based "encryption" is
widely available.  What's included here is built on top of that -- a system
that allows mapping nice human-readable names to various smart-home actions,
and the ability to define arbitrarily complex scenes, including the ability
for scenes to reference other scenes, allowing construction of a more modular
system.

The "tplink" code can be run directly from CLI, or used as a Python library.
Example cgi-servers are provided that render a bunch of buttons to control
individual lights and scenes, and to animate a "party lights" sequence that
slowly adjusts the color of RGB bulbs for a festive effect.

