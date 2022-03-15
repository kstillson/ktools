
## ++ktools
   - backups: generalize & publish rclonedock and rsnapshot configs
   - dns-and-dhcp: generalize & publish dnsdock
   - general wisdom: lots of writing
   - keymaster: generalize & publish kmdock
   - monitoring: generalize & publish filewatchdock, nagdock, procmon
   - services: decide what to keep, generalize & publish, subst links
   - syslog: generalize & publish syslogdock
   - tools-for-root: anything to prune from "q" ?
   - tools-for-users: doc
   - Tplink: generalize & publish tplink.py and related tools
   - add neotree or at least extracted elements...?

## General
   - new name for ktools ?  (Mauveine?  #8D029B)

## MILESTONE: ready for peer review ...?

## Prep for homectrl
   - tidy up pylib/k_gpio
     - https://learn.adafruit.com/cooperative-multitasking-in-circuitpython-with-asyncio?view=all
     - https://circuitpython.readthedocs.io/en/latest/shared-bindings/keypad/index.html
   - add RPi.GPIO to circuitpy_sim
      - graphical interface for inputs and outputs
   - k_auth: tidy, doc, test, and add cmnd to hash

## Homectrl -> ktools
   - move homectrl to ktools and rebind to pylib
      - add tests based on circuitpy_sim
   - change to Makefile based, add remote installation

