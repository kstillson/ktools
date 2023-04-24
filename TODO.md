
# bugs to fix

  - settings: OVERRIDE_ doesn't seem to work from shell for ktools_settings;
    do the examples showing overrides in settings.py actually still work?

  - make for things like services/keymaster/km_helper fail until
    kcore is installed.  breaks the normal make,test,install order.

  - restarting nagdock is incorrectly changing vol group ownership
    to 200360, when should be dwww.

  - add a warning for "command:" contents in non-test [vols]

# doc bugs to fix

  - and simple user-manual for adding hosts/secrets for using pcrypt/km

  - doc: add section about security from structure and layers rather than trying
    to have bullet-proof code...  Assume code has vulns and things will get popped;
    use structure to make minimize harm and recovery time.

# new subsystems

  - add example homesec client modules...?
  - iptables abstraction (easier to read/write/analyze) + assoc. tools

# homectrl new features

  - add RPi.GPIO (i.e. buttons) to circuitpy_sim and kcore/gpio
  - graphical interface for inputs and outputs

# new project name?

  - new name for ktools?
    - kcore?  kdev?  Mauveine?, kwisdom?, kwizdom?, kwizmet?
    - nb with k*: possible confusion w/ kuberneties
    - Peter T: Stillery

# other general thoughts

  - Makefile: add BUILD_SUDO_OK, etc/check-sudo-ok
  - publish launchpad?
  - publish browser launchers?
