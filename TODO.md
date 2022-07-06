
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
     - update pylib/setup.cfg:url
     
## ---------- MILESTONE: ready for peer review ...?

## other ideas & improvements
   - Makefile: add BUILD_SUDO_OK, etc/check-sudo-ok
   - iptables abstraction (easier to read/write/analyze) + assoc. tools

## deferred homectrl related
   - add RPi.GPIO (i.e. buttons) to circuitpy_sim and kcore/gpio
   - graphical interface for inputs and outputs
   - homectrl push update to all

## docker improvements
   - :prep needs to set up /rw/dv/...
     - docker-containers/gitdock/Makefile:# TODO!: need to provide code to generate host-keys and put them in place, and
   - need a :prep that sets up things like network docker2
   - most docker-container tests fail when run off of jack
