
# queued minor improvements

  - hc: run scenes concurrently, even without --quick

# new subsystems

  - add homesec client modules...?
  - iptables abstraction (easier to read/write/analyze) + assoc. tools

# homectrl new features

  - add RPi.GPIO (i.e. buttons) to circuitpy_sim and kcore/gpio
  - graphical interface for inputs and outputs
  - homectrl push update to all

# docker improvements

  - docker-containers needs a :prep
    - set up /rw/dv/...
    - sshdock/gitdock need generated host-keys
    - idempotent setup of docker networks

# new project name?

  - new name for ktools?
    - kcore?  kdev?  Mauveine?, kwisdom?, kwizdom?, kwizmet?
    - nb with k*: possible confusion w/ kuberneties

# other general thoughts

  - Makefile: add BUILD_SUDO_OK, etc/check-sudo-ok

