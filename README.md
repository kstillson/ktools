# ktools

## About The Project

This is a collection of services, tools, and libraries, intended for
moderately knowledgeable owners of Linux and Circuit-Python based systems.

Some highlights:

- A smart-home control system

- A home security system (integrated with the smart-home system)

- A collection of scripts and Docker containers designed to provide
  security-focused services, monitoring, and administrative automation for a
  home-network of Linux servers (big ones and little ones like Raspberry PIs)

- Docker infrastructure for quick and easy maintenance of the provided
  containers, and simple addition of new ones

- A Python library that underpins all of the above.

  This library has two founding principles:

  1. Platform abstraction: I commonly run Python in 4 different ways:
     (a) Python 3 on large servers, (b) some legacy Python 2,
     (c) Raspberry PIs, and (d) Circuit Python (a Python subset created
     by Adafruit for tiny microcontrollers).

     I've been frequently frustrated by incompatibiilties between these 4
     modes, and want an abstraction layer that allows the exact same code to
     run on all of them.

     For RPi's and Circ-py, I'm generally using GPIO pins and Neopixels.
     Large servers generally don't have easily acceible pins, so I use
     graphical libaries to simulate them.  This allows me to develop code
     intended to run on the tiny platforms on nice large platforms with full
     IDEs, pytest, PDB, etc, and only move onto the tiny platforms once the
     code is just about done.

  2. Dependency cutting: I acknowledge that modern Python has put a lot of
     work into virtual environments and automatic dependency tree resolution
     with things like PIP.  But from a security and reliability perspective,
     things like PIP make me *very nervous*.  It's way too easy for folks to
     put poor quality (or deliberately malicious) code into public repos, and
     for other projects to start depending on it.

     This library provides the minimal set of functionality I need for "most"
     of my projects that goes beyond the Python built-in libaries, and has
     almost no dependencies other than those built-in libraries.  It does not
     try to be all things to all people- it focuses on minimal code and
     minimal complexity to provide just what you need as a decent baseline.

  Here's some highlights of the provided functionality:

   - A mechanism that provides authentication and automated secret retrieval
     without needing to store private keys or other secrets in plain-text on
     either the server or the clients.

   - A very simple to use logging abstraction that integrates level filtering
     for various outputs (files, stdout, stderr, syslog), as well a web-based
     log retrieval.

   - A web server and client designed for simplicity of use, and which also
     provides a uniform interface for Python 2 or 3, Raspberry PI, and Circuit
     Python.  Also includes a bunch of Google-engineering-inspired "standard
     handlers" that make remote monitoring and debugging easier.

   - A GPIO and Neopixel abstraction that works on full Linux, Raspberry PIs,
     and Circuit Python boards.

The collection represents years of tinkering and fine-tuning, and it is hoped
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
modules are being published in their not-fully-tangled form.  You're welcome
to help out via pull requests, or just wait for me to get to it.

As an example, much of the system current has various assumptions about
directory structures.  Most Debian/Ubuntu users won't find my directory
choices disturbing, but usually open-source projects allow users to choose
where things should be installed.  It turns out that refitting a complicated
system with many hard-coded directory assumptions is challenging.


## Makefile's

The project uses GNU Linux Makefile's.  A bit old fashioned, I know.  And the
code is generally in Python or bash, i.e. no compilation phase, which might
make "Make" seem like an odd choice.  However, I like the way Makefile's
document dependencies and how things are to be combined, tested, and deployed.
Even when an overall process becomes complicated, well-written Makefile's
remain small and reasonably easy to understand.

  * "make prep" is a custom rule I added, which does some one-time preparatory
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
    directory to build them all, or see the "make everything" target (below).
  
  * "make test" runs unit and/or integration tests.  For servers and Docker
    containers, this involves actually starting the systems up and peppering
    them with tests to confirm operation.
  
  * "make install"- for libraries and services, copies files into their
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
  toggle the behavior...?

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
but chances are you'll end up missing out on some of the key benefits.  For
example, to get the full value of running your own DHCP and DNS services, you
really need to understand how the configuration is used to create pseudo
subnets with different levels of trust.

- - -

## homesec: a highly customizable home security system framework

Homesec is essentially a simple state machine, with states like "armed",
"disarmed", "alarm", etc.

Various triggers move between the states, or cause actions depending on the
current state.  For example, if the system is in the state "someone is home,"
then a trigger that an external door has been opened might just ring a chime.
However, a trigger saying "user 1 is leaving" could cause the system to decide
no-one remains at home, and enter the "armed" state.  Then that same door
trigger would move to "alarm triggered" state, which turns on some lights,
sends a cellphone push alert, and speaks an announcement over the home audio
system that "alarm triggered, 30 seconds to disarm."  If the system isn't
moved to the "disarmed" state within that period, it moves to the "alarm"
state, which turns on more lights, pushes more phone messages, and perhaps
turns on some annoying sirens.

Triggers are HTTP get requests, with an in-hand application layer
authentication system (based on shared secrets), and designed to be simple
enough so it can run on very small devices, like the Raspberry Pi Zero-w's,
which are what generate most of the author's door, window, and motion sensor
signals.

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
passphrase.  KM then de-crypts the secrets into local memory.  Clients can then
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
network-wide cold-start -- once it's done, all the waiting services get their
bootstrap secrets and move to their serving states.

- - -

## tools: stand-alone Linux command-line tools

  * q: a collection of Linux shortcuts, tools, and bash tricks.  Hopefully it
    will eventually be detangeled so the parts that are hopelessly bound with
    the details of the author's personal configuration can be separated out.
    But it's being published anyway. because this script contains considerable
    wisdom in using and managing a small-to-medium fleet of Linux systems, and
    contains a repository of bash tips and techniques that provide a good
    reference for such things.

  * iptables_log_sum: summarize rejected packets from iptables logs.

And a number of user-oriented tools...

  * ratelimiter: incorporate easy rate-limits into shell scripts

  * run_para: run commands in parallel, showing their real-time output in a
    dashboard and (optionally) keeping an organized output transcript.

- - -

## home-control: smart-home CLI and web service

home_control ("hc") can be used as a Python library, stand alone command, or
easily be wrapped into a web service, or a Docker-based micro-service.
Examples of each of these are provided.

HC supports arbitrarily complex scenes, i.e. multiple devices reacting in
different ways to a single command.  Scenes can include other scenes, which
allows constructing complex arrangements elegantly and with little repetition
even when some elements are shared between scenes.  By default all devices are
contacted concurrently, which can give a nice dramatic effect when changing
lots of lights at the same time.  Scenes can also contain delayed actions,
i.e. sequences of events triggered by a single scene command.

HC uses a plug-in based mechanism to control actual external hardware devices.
Currently plug-ins are provided for TPLink switches, plugs, and smart-bulbs
(as this is primarily what the author uses), and for sending web-based
commands.  Additional plug-ins are reasonably easy to write, and hopefully
more will come along over time.

Why TPLink?  Besides having reasonable reliability and cost, TPLink modules
have a local server that allows manipulation and querying via local network
HTTP.  i.e. you can control them from your own systems without needing to
depend on cloud integration.

