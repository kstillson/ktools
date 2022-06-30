
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

PLAIN_TARGETS := $(wildcard *.py *.html *.md)

USER := $(shell whoami)
ifeq ($(USER),root)
	INSTALL_DIR := /usr/local/ktools/home-control
else
	INSTALL_DIR := $$HOME/home-control
endif
include ../../common/Makefile-unstaged

SHELL := /bin/bash

# ---------- custom targets

install: install-stamp

install-stamp: $(PLAIN_TARGETS)
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,rw /; fi
	mkdir --mode 755 -p $(INSTALL_DIR)
	$(MAKE) common_install
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,ro /; fi

# There's testing of the underlying library at the pytools level.  The 
# added-on service is very thin; not much to test, and the hcdata_* files
# are site-specific.  Not sure there's much to test at this layer.
test:

update: all install


# ---------- pass-throughs

clean: common_clean

comp: common_comp

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)

