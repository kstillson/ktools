
# Services

These all provide their services with reasonably simple web-server front-ends
(i.e. accepts GET requests, not fancy POST or XML formatted web-services),
generally intended to be access both directly by human users and by automated
systems (either for direct use or at least for monitoring).

All of these services (except procmon) are intended to be wrapped into Docker
micro-service containers, see the directories with the matching name under
../../containers.  These should all run fine outside a container, but
see ../best-practices for why that's not advised.

Below is a quick overview, but all of these have much more details in the
individual source directories.


## filewatch: a status file monitoring system

Filewatch is intended to do things like watch a list of .log files that are
expected to change regularly, and raise an alarm if their last-change
time-stamps become unacceptably old.  It has a few other features too.


## home-control: web front-end for smart-home controller

This is really just a trivial web-service wrapper around the
pylib/home-control system, and the example configuration files from the
original author's smart-home setup, so you can build your configuration based
on a realistic example.


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

Triggers are http GET requests, with an in-band application layer
authentication system (based on shared secrets), and designed to be simple
enough so it can run on very small devices, like the Raspberry Pi Zero-w's,
which are what generate most of the original author's door, window, and motion
sensor signals.


## keymaster: solving the digital secret bootstrapping problem

It's never a good idea to include plain-text secrets in code.  They're too
easy to extract and you have to start being very careful about things like
backups.  But automated systems need to talk to each other, and that often
needs authentication.  How do these systems get the secrets they'll need,
whether these are shared secrets, private keys, or whatever else?

Keymaster ("KM") is a secrets server.  The secrets are stored in an encrypted
text file.  When the server starts up, it does not have the key to unlock this
data.  An authorized user must access the web-page and provide the encryption
pass-phrase.  KM then de-crypts the secrets into local memory.  Clients can
then request secrets, but only according to strict rules.  For example, the
requestor's source IP address and which key they want must match expectations
exactly.  Even a single unexpected request causes the KM to throw away all its
decrypted data and raise an alarm, both signaling that something is very wrong
and that a human needs to come provide the decryption password again, once
things are safe.

Clients that use KM can start up automatically, but need to be able to
gracefully retry for long periods -- long enough for the human to provide the
unlock key.  In this way, all services can auto-start, but ones that need
secrets won't actually reach their serving state until KM is unlocked.
Unlocking KM is the only manual action a human needs to take upon a
network-wide cold-start -- once it's done, all the waiting services get their
bootstrap secrets and move to their serving states.


## procmon: Linux process white-list security monitor

Regularly scans the list of running processes on a server, and compares it
against a configured allow-list.

Procmon has to be run outside containers, so it can see the whole-system
process list.  Given this privileged perch on the real host, it also has a few
other security-monitoring type checks it can perform.
