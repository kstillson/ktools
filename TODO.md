
## Prep
   - test default handlers under circuitpy
      - remote_addr & group matches

## NeoTree
   - rebind neotree to pylib and verify under circuitpy_sim
   - add fader to animation logic
   - add proper web interface

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

## General
   - new name for ktools ?  (Mauveine?  #8D029B)

## Prep for homectrl
   - tidy up pylib/k_gpio
   - add RPi.GPIO to circuitpy_sim
      - graphical interface for inputs and outputs
   - k_auth: tidy, doc, test, and add cmnd to hash

## Homectrl -> ktools
   - move homectrl to ktools and rebind to pylib
      - add tests based on circuitpy_sim
   - change to Makefile based, add remote installation

