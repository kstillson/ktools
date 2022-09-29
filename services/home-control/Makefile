
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

PLAIN_TARGETS := $(wildcard *.py *.html)

USER := $(shell whoami)
INSTALL_DIR ?= $$HOME/ktools/home-control
include ../../etc/Makefile-common

SHELL := /bin/bash

# ---------- custom targets

# There's testing of the underlying library at the pytools level.  The 
# added-on service is very thin; not much to test, and the hcdata_* files
# are site-specific.  Not sure there's much to test at this layer.
test:
	@echo "not much to test at this layer..."

update: all install


# ---------- pass-throughs

clean: common_clean

comp: common_comp

install: check_kcore_installed common_install

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)

