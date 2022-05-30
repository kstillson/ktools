
## ++ktools tech
   - jack make e seems to work up through rclonedock:Test, which triggers keymaster error:
        2022-5-29 23:38:51: CRITICAL: unsuccessful key retrieval attempt keyname=rclone, reg_hostname=test-rclonedock, client_addr=192.168.2.1, username=, status=Wrong hostname. Saw "192.168.2.1", expected "test-rclonedock".
        how did this work before?
	  + looks like old /ulb/kmc would query host "km" which is 2.9, rather than keys, which is 1.2.
	  + need a docker-specific host override for "keys" -> 2.33 ?  nope.
	
   - nagdock test fails on jack
   - ~all docker tests fail on blue
   - webdock
   - procmon not missing kmdock ?
   - review non-doc TODO's
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

## General
   - new name for ktools ?  (kcore?  kdev?  Mauveine?  #8D029B)
     A: kwisdom/kwizdom?  (nb with k*: confusion w/ kuberneties)


## ---------- MILESTONE: ready for peer review ...?

## deferred homectrl related
     - h/control:ext -> hc.py (needs kcore in webdock, which probably means conversion to ktools-based build)
   - add RPi.GPIO (i.e. buttons) to circuitpy_sim and kcore/gpio
      - graphical interface for inputs and outputs
   - homectrl remote update (?)

## Other
   - keymaster: add last used key date
   - search for things that need to be rebound / updated to new ktools interfaces (e.g. art-projects)
