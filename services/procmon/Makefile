
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

PLAIN_TARGETS := $(wildcard procmon *.py)

USER := $(shell whoami)
ifeq ($(USER),root)
	INSTALL_DIR := /usr/local/ktools/procmon
else
	INSTALL_DIR := $$HOME/ktools/procmon
endif
include ../../common/Makefile-unstaged

SHELL := /bin/bash

# ---------- custom targets

$(TEST_LOG): $(wildcard *.py tests/*.py)
	./procmon --logfile - --nocow --nodmap --noro --output '' --queue '' --test --whitelist procmon_whitelist_test.py |& tee /dev/stderr | grep "all ok"
	python3 procmon_whitelist.py	# checks syntax of the whitelist file.
	echo "passed" > $(TEST_LOG)


# Can't have install depend on $(INSTALL_TARGETS) the way it should, because
# that triggers the install patterns from Makefile-unstaged to run *before*
# the custom logic here, which attempts an install and fails if ROOT_RO.
# So the solution is to always run this :install target, and rely on the
# incorporated :common_install target to not doing anything if there's nothing
# to be done (i.e. an unnecessary double re-mounting of the root drive).
# TODO(defer): seems like we should be able to do better.  Perhaps the ROOT_RO
# logic should be moved into Makefile-unstaged?  Sounds good, but would require
# logic in there to avoid unnecessary root remounts if the install_dir doesn't
# actually require it...
install: $(INSTALL_DIR)
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,rw /; fi
	$(MAKE) common_install
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,ro /; fi


# ---------- pass-throughs

clean: common_clean

comp: common_comp

test: common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)
