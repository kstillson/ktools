## ++ktools tech
   - review non-doc TODO's
     - pylib/kcore/webserver_base.py:    # TODO: allow passing port to constructor OR start method.
     - pylib/tests/kcore/test_webserver.py:# TODO: test shutdown
     - pylib/home_control/plugin_web.py:  # TODO: support backgrounded request for non-debug mode.
     - pylib/circuitpy_sim/Makefile:# TODO: need to include subdirs (e.g. adafruit_esp32spi) and their contents.
     - services/homesec/data.py:# TODO: defer to private.d ...?
     - services/home-control/home_control_service.py:TODO: add robots.txt (perhaps default handler...?)
     - services/keymaster/Makefile:# TODO: not obvious what a good install target dir would be.
     
     - docker-containers/filewatchdock/Makefile:# TODO: move to a separate service...
     - docker-containers/gitdock/Makefile:# TODO!: need to provide code to generate host-keys and put them in place, and
     - docker-infrastructure/Makefile:# TODO: add some tests
     - docker-infrastructure/d-cowscan.py:# TODO: move ignore list to private.d

   - re-confirm virgin build process
     - (pi2) :everything didn't run :prep
     - (pi2) wrong perms for some py sys libs; fix umask on initial sudo'd pip?
     - ? chmod 444 /sys/class/dmi/id/product_uuid
   - make e -> make all ?

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
