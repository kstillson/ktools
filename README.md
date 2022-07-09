# ktools

- - -

## About The Project

This is a collection of computer-security-first services, tools, and
libraries, intended for moderately knowledgeable owners of Linux and
Circuit-Python based systems.

Some highlights:

- A smart-home control system

- A home security system (integrated with the smart-home system)

- A mechanism that provides authentication and automated secret retrieval
  without needing to store private keys or other secrets in plain-text on
  either the server or the clients.

- A collection of scripts and Docker containers designed to provide
  monitoring, maintenance and other administrative automation for a
  home-network of Linux servers (big ones and little ones like Raspberry PIs)

- Docker infrastructure for quick and easy maintenance of the provided
  containers, and simple addition of new ones

- A Python library and tools that underpin the above and a fair bit more.

- - -

## About the Design Philosophy

I try hard to make my systems minimal: in the volume of the code, the
complexity of the abstractions, and the external dependencies.  See
etc/check-package-deps.sh for the small list of requirements.

*It is my hope and intention that you will review my code and pick out the
pieces you want, rather than unquestioningly using the whole system.*

To this end, FAIR WARNING: **This code contains a simplistic tracking system.**
Under some circumstances it can "call home," and let me know you're using it.
Perhaps you consider this a fair price to pay for getting free functionality,
or perhaps you'd prefer it didn't.  You're going to have to read at least as
much as the top-level Makefile to turn it off.

Why do this?  As a warning and a reminder: when you download code from the
Internet, it can do *ANYTHING* -- violate your privacy, penetrate your
security, burrow into your system and create vulnerabilities, either
deliberately or because of a lack of knowledge of its authors.  Some
open-source projects have many contributors, and hopefully those many eyes
will catch bad behavior.  But most FOSS has a small enough team that
collusion or lack of review is absolutely possible.

I put in the extra effort to make my systems simple so you can and will read
and understand the code; so you will get into the habit of not entirely
trusting FOSS; and so you will put pressure on others that they also make
their code and dependencies simple enough that shear complexity does not
force you to accept software without review.

- - -

## About The Author

Ken Stillson retired from Google's central security team in 2021.  He left
with the rank of "Senior Staff" (level 7 out of 9).  Before that, he worked at
MITRE / Mitretek, assisting the US Government with various telecommunications
and security projects.  He left Mitretek as a "Senior Principal" (one level
shy of "Fellow"), and earned a "Hammer Award" from the then US Vice President,
for work that "makes the government work better and cost less."

Ken <<ktools@point0.net>> is now a maker, tinkerer, aspiring artist, and
free-range hacker (in the good sense, of course).

- - -

## Contents Overview

<img align="left" src="etc/graphviz/overview.png">


**docker containers**: The services can stand alone, but it's generally better when services are run in a single-purpose containers (see the "general wisdom" section for why).  These "containers" are just a minimal shell to accomplish that.

The **"tools"** come in several flavors, located in different parts of the directory tree:

- [tools for root](tools-for-root/README.md)
- tools for users: [general](pylib/tools/README.md) and [smart-home control](pylib/home_control/README.md)
- tools for docker:  [docker infrastructure](docker-infrastructure/README.md)
 
<img src="etc/1x1.png" height=150>  <!-- slimy way to force a break to beyond the image -->


pylib/**kcore** is a collection of reasonably low-level abstractions needed to implement all this other stuff.  

See the included [readme](pylib/kcore/README.md) for a full description.  Some highlights:

   - The no-plaintext-secrets authN and secrets exchanger mentioned above.

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

- - -

## Getting started

@@ TODO(doc)

