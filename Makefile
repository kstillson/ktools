
# TODO(doc)

# control variables:
#
# BUILD_SIMPLE
# BUILD_SUDO_OK
# BUILD_DOCKER_CONTAINERS
# SUBDIRS

# Handy Makefile reference: https://makefiletutorial.com/

TOP_TARGETS = all clean comp install test uninstall update
SUBDIRS ?= pylib tools-for-root services docker-infrastructure

ifeq ($(BUILD_DOCKER_CONTAINERS), 1)
  SUBDIRS := $(SUBDIRS) docker-containers
endif

SHELL := /bin/bash
include etc/Makefile-colors

# ---------- standard targets

all:	prep
	@if [[ "$BUILD_DOCKER_CONTAINERS" != "1" ]]; then printf "\n  $(YELLOW)NOTE: $(RESET) docker-containers/... not included in the build.\n         If you think you want it, check README.md and then set 'BUILD_DOCKER_CONTAINERS=1'.\n\n"; fi

# This also includes "all"; both rules will run.
$(TOP_TARGETS): $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

# ---------- special additions to common targets

clean:
	rm -rf home-control/__pycache__ etc/prep-stamp .pytest_cache
	@printf "\n  NOT cleaning $(YELLOW)private.d/$(RESET) as can contain valuable data modified outside of make.  remove manually if you're sure.\n\n"


# ---------- 1-time preparation sequence

prep:	etc/prep-stamp

etc/prep-stamp:	private.d/kcore_auth_db.data.pcrypt private.d/keymaster.pem private.d/wifi_secrets.py services/homesec/private.d/data.py
	etc/check-package-deps.sh
	@pgrep docker > /dev/null || printf "\n\n$(YELLOW)WARNING $(RESET)- docker daemon not detected.  docker-containers/** can't build or run without it.\nYou probably want to do something like:\n  sudo apt-get install docker.io"
	touch etc/prep-stamp

private.d/kcore_auth_db.data.pcrypt:
	touch $@

private.d/keymaster.pem:   private.d/cert-settings
	@if [[ -f private.d/keymaster.key ]]; then printf "\n$(RED)ERROR $(RESET) dont want to overwrite private.d/keymaster.key, although private.d/cert-settings apears to be more recent.\nPlease manually remove 'private.d/key*' if it really is time to generate a new key,\nor run 'touch private.d/keymaster.pem' to keep your current keys and move on.\n\n"; exit 2; fi
	source private.d/cert-settings && \
	  openssl req -x509 -newkey rsa:4096 -days $$DAYS \
	    -keyout private.d/keymaster.key -out private.d/keymaster.crt -nodes \
	    -subj "$${SUBJECT}/CN=$${KM_HOSTNAME}/emailAddress=$${EMAIL}" \
	    -addext "subjectAltName = DNS:$${KM_HOSTNAME}"
	cat private.d/keymaster.crt private.d/keymaster.key > private.d/keymaster.pem
	chmod go+r private.d/keymaster.crt
	chmod go-r private.d/keymaster.key private.d/keymaster.pem

private.d/cert-settings:
	mkdir -p private.d
	cp -n etc/cert-settings.template private.d/cert-settings
	editor private.d/cert-settings

private.d/wifi_secrets.py:
	cp -n etc/wifi_secrets.template private.d/wifi_secrets.py
	editor private.d/wifi_secrets.py

services/homesec/private.d/data.py:
	mkdir -p $(shell dirname $@)
	touch $@


# ------------------------------------------------------------
# Build stamps
# 
# "make" does comparisons between file modification time-stamps to determine
# which operations need to re-done.  if x depends on y, and y depends on z, and
# the user says "make x", then make compares all the timestamps, and if x is
# later than both y and z, is declares that there is "nothing to do" to make x.
# 
# Occasionally a make-based process either does not result in updated files
# (e.g. testing), or there is a complex network of dependencies that could use
# simplifying.  In either case, stamp files are a good solution.
# 
# Stamp files exist only for their modification date-time; they're usually
# empty.  The idea is that you have a make target depend on stamp file, and then
# have the make rule update that same stamp (usually using the Linux "touch"
# command) as the last step in its process.  The last step is used to make sure
# the stamp file isn't updated in the case of a rule that fails part-way
# through a sequence of commands.
# 
# The ../.gitignore file is set to not upload *-stamp files to git, to make
# sure that build progress on one machine doesn't confuse another.  This means
# this stamp files should start-off missing, meaning that all rules which
# depend on a stamp file should run.  As each rule is run, various stamp files
# are updated, which means don't need to be run again the next time you run
# make.
# 
# But what if you do want something to be run again for the next make?  Well,
# you can either manually remove stamp files (which is generally safe- at worst
# it will only cause some unnecessary work during the next make), or use the
# make "clean" target to reset things for you.  That's ideal if you want to
# rebuild parts of the tree, but aren't sure which stamp files are for what.
# Doing a "make clean" in a particular subdirectory will remove only the stamp
# files relevant to that part of the tree.
# 
# It's also possible for the Makefile author to write rules specifying what
# other files (source, configuration, etc) the stamp file depends on.  This
# generally ensures that the presence of a stamp file won't cause build steps to
# be skipped because a stamp file exists when real dependencies have changed.
# 
# So, if you're going to enumerate stamp file dependencies, what's the point in
# the stamp file?  Why not just have the target that would depend on the stamp
# file directly depend on the stamp file's dependencies?  Well, truthfully it's
# more aesthetic than functional.  It allows complex make rules to be broken
# into multiple simpler pieces, and provides a convenient point of reference for
# user's to query the last time a build operation was done, or to easily select
# parts of the build tree to force a redo on (by removing stamp files) or to
# inhibit rebuilding (by manually updating a stamp file).
#
#
# wrt test.log
#
# Note: stamp files are *usually* empty.  But throughout this system, tests
# save their output into files (named test.log), and these are effectively
# used as stamp files to indicate when testing was last run.  Makefile
# dependencies on source files are provided, so this scheme is smart enough to
# realize you need to re-test if source changes.  However, if tests fail for
# some environmental reason, you fix that and then try to re-run the tests,
# make will say "make: Nothing to be done for 'test'.  This is because the
# test.log stamp file does not depend on the environment, and thus doesn't
# "see" the fix you made.  Either "make clean" or manually remove test.log
# and then "make test" should re-run the tests.

