# kcore python library

kcore_pylib consists of 4 packages:

- - - 
## kcore

kcore is a set of reasonably-low-level reasonably-common operations or
simplicaitions, as described below.

Several of the modules are split into between a primary and a _base file.  The
primary file imports the _base into its own namespace, so you shouldn't
generally need to import the _base file separately.  Why the split?  Because
the primary version makes use of feature(s) not available in Circuit Python.
If you check out ../circuitpy_lib, you'll see that there are "_circpy"
specific versions of these modules that re-use the pylib/kcore _base code.

TODO: is it possible undo the split and have something like a #ifdef to stop
Python from parsing the circpy-unfriendly bits..?  dunno...

Note: originally most of this code was intended to work seemlessly with both
python2 and python3


### auth.py

auth is a module designed to generate and validate authentication tokens,
primarily for the keymaster project (see ../services/keymaster).  The main
feature is that tokens mix-in machine-specific details, so that tokens
are hardware-locked to a specific machine.


### common.py

common provides some simple data manipulators, and abstractions that mostly
try to hide python2 vs. python3 differences.

common really has two parts: a logging system and a web client.

The logging system is similar in concept to built-in Python logging, but also
allows automatically routing messages to stdout, stderr, and/or syslog, based
on message priority levels, and also integrates support for the /logz
web-handler, a default handler provided with webserver.py (see below).

When using python3, the web client is really a very thin wrapper around the
"requests" module, perhaps providing a slightly simpler interface.  When using
python2, the primary purpose of this module is to create an interface that is
identical to the python3 interface, i.e. it partially emulates the "requests"
module.


### docker_lib.py

A bunch of Docker related library routines, primarily used by
../docker-infrastructure.

Can do things like locate the copy-on-write directory for a container,
determine if the latest built image is tagged "live", and provides a bunch of
abstractions that help with automated Docker image unit testing.


### html.py

A very simple set of functions that take various forms of plain text and lists
and output HTML.


### uncommon.py

More (Circuit Python unfriendly) library routines, but ones of a more esoteric
nature, so removed from common.py to declutter it somewhat.

Provides features like:

  - a specialized dict-class derivative, that enables serialization when the
    value-side of the dict is a @dataclass.

  - ability to easily run some Python commands and capture their stdout/stderr.

  - easily pass data through GPG for symmetric (password) en-de/crypt.

  - safely drop root priv's


### varz.py

Provides a simple singlton database of key/value pairs which is integrated
with the /varz default handler from webserver.py

The idea is that it's very easy for programs to "instrument" their internal
operational values for easy external inspection.  It's easy to bump named
counters, set time-stamps for the last time some important (named) event
happened, or just set values to indicate a current status.

This enables debugging, or just checking what the internal state of a program
is, accessible entirely through an easy web-interface (provided by
webserver.py), or via an API, to help with things like unit testing.

Security note: varz has no authentication requirements for either the web or
local API, so never expose secret data!


### webserver.py (and webserver_base.py)

Attempts to do most of the annoying boiler-plate stuff, so you can establish a
web-server with full custom handlers with just a few lines of code.

Supports plain http and TLS, get and post methods, regex-based handler lookup,
a bunch of default handlers, and is integrated with the common.py logging and
varz.py systems.

webserver_base.py is Circuit Python friendly, and contains all the logic that
has nothing to do with networking, so Request and Response abstractions,
handler finding and management, default handlers, and the like.

webserver.py basically layers the fully-featured (and thus circpy-unfriendly)
bits on-top: networking, threading, TLS, and logging.


- - - 
## ktools

The tools subdirectory provides several command-line utilities that can also
be imported as Python libraries.


### kmc.py: key-manager client

../services/keymanager provides a service for web-based secrets retrieval
(passwords, keys, etc).  "kmc" is the client interface for that service.  It
provides kcore/auth based authentication, retries, etc.


### pb-push.sh

Provides a simple interface for sending push notifications via the "Push
Bullet" service.  Integrates with kmc to retrieve access tokens.


### ratelimiter.py

Provides a tool that's easy to integrate with shell-scripts that can cause
actions to be limited to x-per-y-time.  You can have the action fail (i.e. be
skipped) if the rate-limit would be violated, or have the script hold a
command until the limit would be respected.

Note: needs an external file to store desired limits and recent-usage data.


### run_para.py

Runs (command-line) commands in parallel.  Keeps the stdout and stderr of each
job separated, and shows the real-time output of jobs in a dashboard.

See the module doc for various examples of what this is useful for.


- - - 
## home_control: a smart-home control system

Similar to the tools/ directory, this provides a command-line interface that's
also usable as a Python library module.

hc.py sends commands, like "turn on" to "targets."  Targets can be individual
devices (like a lamp), or "scenes" with many devices all doing different
things.

Scenes can include other scenes, which makes it reasonably easy to build
complex arrangements out of simpler building blocks.  Scene commands are (by
default) sent in parallel, making them very fast.

Commands are actually transmitted to smart-home devices through "plugins."
Currently plugins are available for TP-Link (bulbs, plugs, and switches), and
devices which accept fixed web-based GET commands.


- - - 
## circuitpy_sim

This is a library directory that provides a few modules that minic the Circuit
Python API, but use normal Python for their implementation.

Most of these are reasonably simple pass-throughs.  For example,
adafruit_requests.py just passes its functions through to normal "requests".

The one that's a bit special is neopixel.py.  It provides a mock of the
Circuit Python API that draws simulated Neopixels using the Python tkinter
graphics library.

What it all for?  If the circuitpy_sim directory is inserted into Python's
import path (see circuitpy_sim/README.md for specifics), you can run Circuit
Python code on your normal Linux computer.  This allows much quicker and
easier code iteration cycles than having to constantly upload code to a
Circuit Python board, and also allows use of standard Python debugging tools
(e.g. pdb) on your Circuit Python code.

In this way, you can unittest, manually test, and debug Circuit Python code on
a much more capable platform, and only upload it to a real Circuit Python
board once you're getting reasonably close.

NOTE: circuitpy_sim is still in a very early / alpha-type state.  Any
suggestions or additions would be most welcome.

