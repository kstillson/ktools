
# Handy Makefile reference: https://makefiletutorial.com/

TOP_TARGETS = all clean comp install test uninstall update

# specify SUBDIRS as an environment variable for partial work.
# remember that order matters.
#
# Note: docker-containers is excluded from the list of subdirs because
# (a) building docker images requires root privs, and folks would rightly be
#     concerned about a "make all" asking for sudo rights
# (b) building docker images requires the docker-infrastructure/ targets
#     to be INSTALLED before docker-containers can be BUILT.
# (c) buidling and installing docker images needs to be carefully ordered,
#     as some depend on others, and the dependent ones cannot be BUILT
#     until the dependency is INSTALLED (i.e. tagged as :live).
#
# All of this is why the :everything target (shortcut :e) is provided;
# it will build, test, and install everything, all in the right order.
#
SUBDIRS ?= pylib tools-for-root services docker-infrastructure 
SHELL := /bin/bash

# ---------- standard targets

all:	prep common_all

common_all:   # Nothing to do in top-level dir; allow to flow into subdirs.

$(TOP_TARGETS): $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

# ---------- special additions to common targets

clean:
	$(MAKE) --no-print-directory -C docker-containers clean
	rm -rf home-control/__pycache__ common/prep-stamp .pytest_cache
	@echo "NOT cleaning private.d/ as can contain valuable data modified outside of make.  remove manually if you're sure."


# ---------- everything

# Need to build and install pylib first, as it's used in Docker container
# build and testing.  Then need to build and "install" (i.e. mark "live")
# kcore-baseline before other containers, as they're build on-top of the
# "live" kcore image.

everything:
	@printf "\n\n** building, testing, and installing all non-Docker-based libraries tools.\n\n"
	$(MAKE) update   # all -> test -> install
	@printf "\n\n** about to sudo to install pylib tools for root to use; needed for docker building and testing.\n\n"
	sudo --preserve-env=BUILD_SIMPLE $(MAKE) -C pylib install
	@printf "\n\n** building, testing, and installing Docker baseline image.\n\n"
	$(MAKE) --no-print-directory -C docker-containers/kcore-baseline update
	@printf "\n\n** building Docker images\n\n"
	$(MAKE) --no-print-directory -C docker-containers all
	@printf "\n\n** testing Docker images\n\n"
	$(MAKE) --no-print-directory -C docker-containers test

e:	everything   # simple alias for "everything"


# ---------- 1-time preparation sequence

prep:	common/prep-stamp

common/prep-stamp:	private.d/kcore_auth_db.data.pcrypt private.d/keymaster.pem private.d/wifi_secrets.py services/homesec/private.d/data.py
	@pgrep docker > /dev/null || echo "WARNING- docker daemon not detected.  docker-containers/** can't build or run without it.  You probably want to do something like:  sudo apt-get install docker.io"
	touch common/prep-stamp


private.d/kcore_auth_db.data.pcrypt:
	touch $@

private.d/keymaster.pem:   private.d/cert-settings
	@if [[ -f private.d/keymaster.key ]]; then printf "\ndont want to overwrite private.d/keymaster.key, although private.d/cert-settings apears to be more recent.\nPlease manually remove 'private.d/key*' if it really is time to generate a new key,\nor run 'touch private.d/keymaster.pem' to keep your current keys and move on.\n\n"; exit 2; fi
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
	cp -n common/cert-settings.template private.d/cert-settings
	editor private.d/cert-settings

private.d/wifi_secrets.py:
	cp -n common/wifi_secrets.template private.d/wifi_secrets.py
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

