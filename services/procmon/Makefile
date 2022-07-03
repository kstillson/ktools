
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

PLAIN_TARGETS := $(wildcard procmon *.py)

USER := $(shell whoami)
ifeq ($(USER),root)
	INSTALL_DIR := /usr/local/ktools/procmon
else
	INSTALL_DIR := $$HOME/procmon
endif
include ../../common/Makefile-unstaged

SHELL := /bin/bash

# ---------- custom targets

$(TEST_LOG): $(wildcard *.py tests/*.py)
	./procmon --logfile - --nocow --nodmap --noro --output '' --queue '' --test --whitelist procmon_whitelist_test.py |& tee /dev/stderr | grep "all ok"
	python3 procmon_whitelist.py	# checks syntax of the whitelist file.
	echo "passed" > $(TEST_LOG)


install: install-stamp

install-stamp: $(PLAIN_TARGETS)
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,rw /; fi
	mkdir --mode 755 -p $(INSTALL_DIR)
	$(MAKE) common_install
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,ro /; fi


# ---------- pass-throughs

clean: common_clean

comp: common_comp

test: common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)
