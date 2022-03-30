
## ++ktools
   - Tplink: generalize & publish tplink.py and related tools (change to separate docker)
   - TOC / general intro write-up
   - backups: generalize & publish rclonedock and rsnapshot configs
   - dns-and-dhcp: generalize & publish dnsdock
   - general wisdom: lots of writing
   - monitoring: generalize & publish filewatchdock, nagdock, procmon
   - services: decide what to keep, generalize & publish, subst links
   - syslog: generalize & publish syslogdock
   - tools-for-root: anything to prune from "q" ?
   - tools-for-users: doc
   - k_auth: tidy, doc, test, and add cmnd to hash
   - make sure all python is using __doc__ friendly formatting

## General
   - new name for ktools ?  (Mauveine?  #8D029B)

## ---------- MILESTONE: ready for peer review ...?

## Prep for homectrl
   - tidy up pylib/k_gpio
     - https://learn.adafruit.com/cooperative-multitasking-in-circuitpython-with-asyncio?view=all
     - https://circuitpython.readthedocs.io/en/latest/shared-bindings/keypad/index.html
   - add RPi.GPIO (i.e. buttons) to circuitpy_sim and k_gpio
      - graphical interface for inputs and outputs

## Homectrl -> ktools
   - move homectrl to ktools and rebind to pylib
      - add tests based on circuitpy_sim
   - change to Makefile based, add remote installation

## Other
   - search for things that need to be rebound / updated to new ktools interfaces (e.g. art-projects)

## homesec
   - rebind away from django  (flask?  all the way down to ktools?)
