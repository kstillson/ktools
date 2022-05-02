
# Supported meta-targets:  all, clean, test, install, update

PLAIN_TARGETS := procmon procmon_whitelist.py
INSTALL_DIR := /usr/local/procmon
include ../../common/Makefile-unstaged

SHELL := /bin/bash


$(TEST_LOG): $(wildcard procmon*)
	./procmon -t |& tee /dev/stderr | grep "all ok"
	echo "passed" > $(TEST_LOG)

update: all test install


# ---------- custom targets

install: $(INSTALL_DIR) $(INSTALL_TARGETS)
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,rw /; fi
	$(MAKE) common_install
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,ro /; fi

#$(INSTALL_DIR):
#	mkdir --mode 755 -p $(INSTALL_DIR)


# ---------- pass-throughs

all: common_all

clean: common_clean

comp: common_comp

test: common_test

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)
