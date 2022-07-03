## ++ktools tech
   - review non-doc TODO's
      tools-for-root/q.sh:# TODO: The TEST, and VERBOSE options not uniformly implimented.
      services/homesec/ext.py:# TODO: move to addrs into private.d
      README.md:TODO: all the below stuff will eventually be fixed..
      pylib/README.md:TODO: is it possible undo the split and have something like a #ifdef to stop
      pylib/setup.cfg:url = TODO...

      docker-containers/filewatchdock/Makefile:# TODO: move to a separate service...
      docker-containers/nagdock/files/usr/lib/nagios/plugins/check_disk_smb:    # TODO : why is the kB the standard unit for args ?
      docker-containers/nagdock/Test:    '''TODO: At this point, we should be able to re-parse the status file and
      docker-containers/eximdock/Test:# TODO: dependent on Ken-specific config
      docker-containers/eximdock/Test:## TODO: test appeared to pass evne when msg send clearly failed (panic log
      docker-containers/syslogdock/files/etc/syslog-ng/syslog-ng.conf:# See general-wisdom/monitoring.md (TODO: link) for an explanation of the
      docker-containers/rclonedock/Test:# TODO!: dep on /rw/mnt/rsnap/echo-back/test-out
      docker-containers/gitdock/Makefile:# TODO!: need to provide code to generate host-keys and put them in place, and

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
