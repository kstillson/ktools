
## integration phase
   - finish homectrl integrations
   - other home-control client transitions
     - h/control:ext
   
## circuit py evolution
   - merge webserver, webserver_base, webserver_circpy
   - merge common, common_base
   - merge the rest of circuitpy_lib into pylib
   - review kcore for incomp w/ circpy and fix or document

## ++ktools tech
   - backups: generalize & publish rclonedock and rsnapshot configs
   - dns-and-dhcp: generalize & publish dnsdock
   - monitoring: generalize & publish filewatchdock, nagdock, procmon
   - services: decide what to keep, generalize & publish, subst links
   - syslog: generalize & publish syslogdock
   - tools-for-root: anything from "q" to move to private.d ?
   - "d clean" not respecting filter (clears :live, :latest, :prev, etc)
   - make sure all python is using __doc__ friendly formatting
   - noted bugs
     - (pi2) :everything didn't run :prep
     - (pi2) wrong perms for some py sys libs; fix umask on initial sudo'd pip?
   - review TODO's
   - re-confirm virgin build process
     - ? chmod 444 /sys/class/dmi/id/product_uuid 
   
## General
   - new name for ktools ?  (kcore?  Mauveine?  #8D029B)

## ++ktools prose
   - makefiles- lots of explanations and intros
   - TOC / general intro write-up
   - general wisdom: lots of writing
   - tools-for-users: doc

## ---------- MILESTONE: ready for peer review ...?

## deferred homectrl related
   - kcore/gpio: make compat with circpy
   - tidy up pylib/k_gpio
     - https://learn.adafruit.com/cooperative-multitasking-in-circuitpython-with-asyncio?view=all
     - https://circuitpython.readthedocs.io/en/latest/shared-bindings/keypad/index.html
   - add RPi.GPIO (i.e. buttons) to circuitpy_sim and kcore/gpio
      - graphical interface for inputs and outputs
   - homectrl remote installation

## homesec
   - rebind to ktools

## Other
   - search for things that need to be rebound / updated to new ktools interfaces (e.g. art-projects)

