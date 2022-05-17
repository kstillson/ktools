
# Supported meta-targets:  all, clean, test, install, update

PLAIN_TARGETS := procmon procmon_whitelist.py procmon_wl_type.py

USER := $(shell whoami)
ifeq ($(USER),root)
	INSTALL_DIR := /usr/local/procmon
else
	INSTALL_DIR := $$HOME/procmon
endif
include ../../common/Makefile-unstaged

SHELL := /bin/bash


$(TEST_LOG): $(wildcard procmon*)
	## TODO: calling procmon runs sudo for d-map, which will confuse folks on why we want a sudo during a test run.
	## ./procmon --logfile - --nocow --noro --output '' --queue '' --test --whitelist procmon_whitelist_test.py |& tee /dev/stderr | grep "all ok"
	python3 procmon_whitelist.py    # checks syntax of the whitelist file.
	echo "passed" > $(TEST_LOG)

update: all test install


# ---------- custom targets

install: install-stamp

install-stamp: $(PLAIN_TARGETS)
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,rw /; fi
	mkdir --mode 755 -p $(INSTALL_DIR)
	$(MAKE) common_install
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,ro /; fi


# ---------- pass-throughs

all: common_all

clean: common_clean

comp: common_comp

test: common_test

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)

