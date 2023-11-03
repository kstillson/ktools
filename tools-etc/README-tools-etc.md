
# tools-etc

This is a collection of small and simple tools that I consider too trivial,
too informal, or too special-case to deserve placement in one of the more
proper tools directories, but which I figured I'd go ahead and release anyway,
in-case they happen to be of use to anyone.

But I do have a little documentation inside each one, so feel free to take a
look, and make use of anything that appeals to you.


## Contents

- autokey-run: lists all, or a filtered selection, of available autokey
  expansions, and "runs" the selected one.  But rather than pushing the
  output to the keyboard, it's sent to the x-clip copy/paste buffer.
  Side effects (such a launching programs) happen normally.

- button_relay: listen on serial for messages from Arduino/espnow_button_recvr
  (below) and take actions in response to espnow network events.

- m: run-time on-demand filesystem mounter

- party-lights: Slow color animation sequence for TP-Link smart bulbs.

- pb-push: sends push-notifications via the Android Push Bullet app

- speak-cgi: Trivial CGI wrapper for speak.py (below)

- speak: Convert the text on the command-line into speech, and say it.
  (supports a bunch of different speech rendering methods)

- sunsetter: Wait until an offset before/after sunset and then run a command.


## Arduino/

- arduino-filter-boards.py: filter all but whitelisted boards from the
  very-very-long list of supported boards, so picking the right one is easier.

- espnow_button_recvr: listen on espnow network and report events
  via serial port.  Also accepts various ad-hoc commands via serial.
  Intended to be paired with button_relay (above) and receive signals
  from espnow_sleepy_button_sender (below).
  
- espnow_sleepy_button_sender: designed for Adafruit Qt Py esp32-x boards,
  spends most of its time in "deep sleep" waiting for a physical button push.
  Then wakes, transmits button and battery voltage information via espnow,
  and sleeps again.

- kds_arduino_snippets_lib.ino: (code snippets; not directly compilable)
  A collection of useful Arduino code snippets grabbed from various projects.


## Tasker/

The subdirectory ./Tasker has a bunch of my scripts for the Android Tasker
app.  See [README-Tasker](Tasker/README-Tasker.md) for details.


## Arc/ (archived)

- gpg_s: simple wrapper around gpg symmetric encrpytion
  deprecated in favor of pcrypt: pylib/kcore/uncommon.py:symmetric_crypt()

