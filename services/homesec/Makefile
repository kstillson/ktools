
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

PLAIN_TARGETS := $(wildcard *.py *.html *.md)

SUBDIRS_TO_COPY := private.d static templates

USER := $(shell whoami)
ifeq ($(USER),root)
	INSTALL_DIR := /usr/local/ktools/homesec
else
	INSTALL_DIR := $$HOME/ktools/homesec
endif
include ../../etc/Makefile-common

SHELL := /bin/bash

# ---------- custom targets

install: install-stamp

install-stamp: $(PLAIN_TARGETS)
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,rw /; fi
	mkdir --mode 755 -p $(INSTALL_DIR)
	$(MAKE) common_install
	cp -pr $(SUBDIRS_TO_COPY) $(INSTALL_DIR)
	if [[ "$$ROOT_RO" == 1 ]]; then mount -o remount,ro /; fi

$(TEST_LOG): $(wildcard *.py tests/*.py)
	script -e -c "pytest-3 tests" $(TEST_LOG)


# ---------- pass-throughs

clean: common_clean

comp: common_comp

test: common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)

