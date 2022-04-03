
## integrate ktools docker containers with existing ones on jack
   - hs client checks: h/control:ext, h/inst, keypads, trellis1

## ++ktools tech
   - backups: generalize & publish rclonedock and rsnapshot configs
   - dns-and-dhcp: generalize & publish dnsdock
   - monitoring: generalize & publish filewatchdock, nagdock, procmon
   - services: decide what to keep, generalize & publish, subst links
   - syslog: generalize & publish syslogdock
   - tools-for-root: anything from "q" to move to private.d ?
   - "d clean" not respecting filter (clears :live, :latest, :prev, etc)
   - make sure all python is using __doc__ friendly formatting
   - review TODO's
   - confirm pylib wheel-based install still works
   
## ++ktools prose
   - TOC / general intro write-up
   - general wisdom: lots of writing
   - tools-for-users: doc

## ktools virgin build process
   - file needed before basic "build all" will work:
     - need docker-containers/kcore-baseline/private.d/cert-settings
     - need services/keymaster/private.d/km.data.gpg

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
