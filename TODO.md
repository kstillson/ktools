
## integration phase
   - pylib to official pip repo, test install on home-control devices
   - keymaster: key population, testing
   - rebind home-control to kcore
     - auth
     - home-control (<- homesec)
   - other home-control client transitions
     - from above: keypads, trellis1
     - h/control:ext
     - done: h/inst

## ++ktools tech
   - confirm pylib wheel-based install still works
   - backups: generalize & publish rclonedock and rsnapshot configs
   - dns-and-dhcp: generalize & publish dnsdock
   - monitoring: generalize & publish filewatchdock, nagdock, procmon
   - services: decide what to keep, generalize & publish, subst links
   - syslog: generalize & publish syslogdock
   - tools-for-root: anything from "q" to move to private.d ?
   - "d clean" not respecting filter (clears :live, :latest, :prev, etc)
   - make sure all python is using __doc__ friendly formatting
   - review TODO's
   - should :clean remove copied files for docker-containers ?
   - manual setup-prep phase- automate
     - include auth's chmod 444 /sys/class/dmi/id/product_uuid 

## ++ktools prose
   - TOC / general intro write-up
   - general wisdom: lots of writing
   - tools-for-users: doc

## ktools virgin build process
   - file needed before basic "make all" will work:
     - need docker-containers/kcore-baseline/private.d/cert-settings
     - need services/keymaster/private.d/km.data.gpg
   - dirs needed for "make install" to work for docker containers:
     - /rw/dv/TMP                      (droot not root...)
     - /rw/dv/home-control/var_log_hc  (droot not root...)
     - /rw/dv/keymaster/var_log_km     (droot not root...)
   - docket network setup

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
