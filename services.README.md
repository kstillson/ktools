
TODO(doc)


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
