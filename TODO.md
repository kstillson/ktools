## ++ktools virgin build process
   - top level "make test" fails under -C services, because pylib not yet installed.
   - pylib :install doesn't auto-run :all if the wheel isn't built; just gives an error
   - under qmeu, puid read for /sys/class/dmi/id/product_uuid can fail.
     - chmod 444 ?
   - (pi2) wrong perms for some py sys libs; fix umask on initial sudo'd pip?
   - :prep needs to set up /rw/dv/...
     - docker-containers/gitdock/Makefile:# TODO!: need to provide code to generate host-keys and put them in place, and

## treasure hunt
   - A's idea about several analytics collectors- prominantly document #1,
     subtlely document #2, and really hide #3 (dns query only?).  encourage
     code reviews, and make ppl think about foss security.

## ++ktools prose
   - review all doc TODO's
   - makefiles- lots of explanations and intros
   - general wisdom: lots of writing
   - overall spellcheck and markdown linting

## General
   - new name for ktools ?  (kcore?  kdev?  Mauveine?  #8D029B)
     A: kwisdom/kwizdom?  (nb with k*: confusion w/ kuberneties)
     kwizmet ?
     - pylib/setup.cfg:url = TODO...

## ---------- MILESTONE: ready for peer review ...?

## other ideas & improvements
   - iptables abstraction (easier to read/write/analyze) + assoc. tools

## deferred homectrl related
   - add RPi.GPIO (i.e. buttons) to circuitpy_sim and kcore/gpio
   - graphical interface for inputs and outputs
   - homectrl push update to all

## docker container generalization
   - docker-container tests fail when run off of jack
     - filewatch: move to services and add testing mode
     - gitdock: need hostkeys
     - homesecdock: needs testing version of kcore_auth_db.data.pcryp
     - keymaster: needs testing version of kcore_auth_db.data.pcryp
     - nagdock: test is specialized to jack
     - rclonedock: causes km lockdown with real key retrieval attempt
     - rsnapdock: all sorts of problems
     - squiddock: created dir perms (?)
     - sshdock: old testing binding
     - syslogdock: created dir perms (?)
     - webdock: unknown perms prob
