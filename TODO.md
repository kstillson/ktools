## ++ktools tech
   - review non-doc TODO's
     - Makefile:# TODO: sudo for subparts where :everything leaves root owned files...?
     - pylib/tools/pb-push.sh:# TODO: rewrite in python3
     - pylib/tools/pb-push.sh:# TODO: somewhat Ken specific.
     - pylib/kcore/auth.py:TODO: separate out a auth_base that depends only on hashlib, so it can work
     - pylib/kcore/neo.py:  - TODO: other modes...
     - pylib/kcore/gpio.py:TODO: add support for:
     - pylib/kcore/gpio.py:            # TODO: multiple samples...?
     - pylib/kcore/webserver_base.py:TODO: add support for basic auth (with db file compatible with htpasswd...?)
     - pylib/kcore/webserver_base.py:    # TODO: allow passing port to constructor OR start method.
     - pylib/kcore/webserver_circpy.py:TODO: add POST submission parsing.
     - pylib/kcore/webserver_circpy.py:CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')  # TODO: any better way?
     - pylib/kcore/webserver.py:        if tls_key_password: raise RuntimeError('TODO: support tls_key_password')
     - pylib/tests/kcore/test_uncommon.py:''' TODO: DISABLED.
     - pylib/tests/kcore/test_common.py:    # TODO: mock syslog and check it.
     - pylib/tests/kcore/test_common.py:# NB: relies on the author's personal web-server.  TODO: find something better.
     - pylib/tests/kcore/test_webserver.py:# TODO: test shutdown
     - pylib/setup.cfg:url = TODO...
     - pylib/home_control/plugin_web.py:  # TODO: support backgrounded request for non-debug mode.
     - pylib/circuitpy_sim/Makefile:# TODO: need to include subdirs (e.g. adafruit_esp32spi) and their contents.
     - services/homesec/Makefile:# TODO: not obvious what a good install target dir would be.
     - services/homesec/data.py:# TODO: defer to private.d ...?
     - services/homesec/ext.py:if True:  ##@@ TODO:   if DEBUG:
     - services/home-control/home_control_service.py:TODO: add robots.txt (perhaps default handler...?)
     - services/keymaster/Makefile:# TODO: not obvious what a good install target dir would be.
     - services/keymaster/km.py:TODO: under some circumstances (e.g. cert verification failure),
     - services/keymaster/km_helper.py:TODO
     - tools-for-root/tests/test_q.sh:# TODO: a proper test suite for q.sh would take a while, but be valuable.
     - tools-for-root/q.sh:# TODO: The TEST, and VERBOSE options not uniformly implimented.
     - tools-for-root/q.sh:# TODO: can this be simplified?  externalized?
     - tools-for-root/q.sh:# TODO: assumes remote branch is named "master"
     - tools-for-root/q.sh:    # TODO: move to standard location (with autodetect for ro root)
     - tools-for-root/q.sh:        listp)                                                     ## run $@ locally with --host-subst, taking list of substitutions from stdin rather than a fixed host list.  spaces in stdin cause problems (TODO).
     - docker-containers/filewatchdock/Makefile:# TODO: move to a separate service...
     - docker-containers/dnsdock/files/etc/dnsmasq/dnsmasq.hosts:# TODO - provide examples
     - docker-containers/dnsdock/files/etc/dnsmasq/dnsmasq.macs:# TODO - private examples
     - docker-containers/syslogdock/Test:# TODO!: fails on blue: 2022-05-03 13:02:16,168 INFO spawnerr: unknown error making dispatchers for 'syslog-ng': EACCES
     - docker-containers/kcore-baseline/Test:    # TODO: can't find a way to run this in an automated way that looks sufficiently
     - docker-containers/kcore-baseline/Test:    # TODO: launch a local server and test kmc against it.
     - docker-containers/sshdock/Test:## TODO: generalize?  make dep on default account from init script?
     - docker-containers/rclonedock/files/etc/init:	# (TODO: surely there's a better test than this...)
     - docker-containers/rclonedock/Test:# TODO!: dep on /rw/mnt/rsnap/echo-back/test-out
     - docker-containers/rsnapdock/readme-acls.txt:TODO: user must manually generate and populate these:
     - docker-containers/rsnapdock/Test:# TODO!: test fails on blue with something about hostkey validation...  investigate
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
