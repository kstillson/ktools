
## ++ktools tech
   - homesec
     - test in prod
     - change clients to use kcore.auth
   - nagdock test fails on jack
   - ~all docker tests fail on blue
   - add uc.popen ?
   - webdock (holding on homesec transition)
   - review non-doc TODO's
   - re-confirm virgin build process
     - (pi2) :everything didn't run :prep
     - (pi2) wrong perms for some py sys libs; fix umask on initial sudo'd pip?
     - ? chmod 444 /sys/class/dmi/id/product_uuid
   - make e -> make all ?
   - linting?

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
   - change homesec clients to use k_auth rather than kmc
   - h/control:ext -> hc.py (needs kcore in webdock, which probably means conversion to ktools-based build)
   - add RPi.GPIO (i.e. buttons) to circuitpy_sim and kcore/gpio
   - graphical interface for inputs and outputs
   - homectrl remote update (?)

## Other
   - keymaster: add last used key date
   - bashlib ?
   - search for things that need to be rebound / updated to new ktools interfaces (e.g. art-projects)
