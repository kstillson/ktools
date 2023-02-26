
# pylib/kcore Python library

kcore is a set of reasonably-low-level reasonably-common operations or
simplifications:


## auth.py

auth is a module designed to generate and validate authentication tokens.
Internally, this is used for things the Keymaster project
(../../services/keymaster), and the homesec system (../../services/homesec)-
for security sensors to securely trigger alarm events.

The main feature is that tokens mix-in machine hardware-specific details, so
that tokens are hardware-locked to a specific machine.  This means the client
need not store a possible-to-steal secret that represents its identity, making
client backups easier and safer.


## common.py

A grab-bag of functionality used by almost everything else in this system.
common is written to be compatible with Python 2, Python 3, and Circuit Python,
and provides the same functionality regardless of the platform.

Some highlights:

- A multi-level logging system (similar to Python logging, but with a few
  additional features such as web-based log retrieval and syslog integration,
  and availability under Circuit Python).

- A web URL retriever that for Python 3 is basically a thin wrapper around the
  "requests" module, but which provides an identical API for Python 2 and
  Circuit Python that basically emulates the full "requests" module.

- Simple i/o abstractions that include exception handling.

- A simple console text colorizer.


## docker_lib.py

A bunch of Docker related library routines, primarily used by
../container-infrastructure.

It can do things like locate the copy-on-write directory for a container,
determine if the latest built image is tagged "live", and provides a bunch of
abstractions that help with automated Docker image unit testing.


### gpio.py

Provides abstractions for buttons and LEDS that can use the same API on
Raspberry PIs, Circuit Python, and full Python in a simulation mode.


### html.py

A very simple set of functions that take various forms of plain text and lists
and generate HTML.


# persister.py

A simple mechanism for keeping an in-memory cache of a Python data structure
up-to-date wrt a human-readable serialized copy.


# neo.py

Provides abstractions for Adafruit Neopixels that provide an identical API
that works on Raspberry PIs, Circuit Python micro-controllers, full C Python
(using a graphical simulation), and a headless simulation mode.


## settings.py

Provides a unified system for loading settings from a variety of sources, with
a clearly specified prioritzation order.  Settings can come from:

- files or strings containing:
  - yaml, serialized dict (see persister.py), one-per-line name=value pairs
- command line flags
- environment variables that override other types of settings
- environment variables that provide defaults when other settings don't.

Fully integrated with command.special_arg_resolver (i.e. settings can load
file contents, query password values from the user, query keymaster).


## timequeue.py

A simple mechanism for running a queue of events after a time delay, again
with multi-platform support.


## uncommon.py

Another grab-bag of Python library routines, but this is the collection that
doesn't work under Circuit Python, or are a bit to specialized to be "common".

Highlights:

- a specialized dict-class derivative, that enables serialization when the
  value-side of the dict is a @dataclass.

- ability to easily run some Python commands and capture their stdout/stderr.

- easily pass data through symmetric (password) en-de/crypt.

- safely drop root priv's

- a simplified popen interface


## varz.py

Provides a simple singleton database of key/value pairs which is integrated
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


## webserver.py (and webserver_base.py)

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


## varz_prom.py

A thin wrapper around varz.py that adds automatic exporting of /varz values
to prometheus_client, to provied a "/metrics" handler.


- - -

# Other notes

- Originally most of this code was intended to work seamlessly with both
  python2 and python3.  I've since given up on supporting python2, but if you
  find bits-and-pieces of anachronistic Python syntax, it's probably vestiges
  of my py2 support that haven't been cleaned out yet...
