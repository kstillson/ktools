
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

PLAIN_TARGETS := $(wildcard *.py *.html *.md)

SUBDIRS_TO_COPY := private.d static templates

INSTALL_DIR ?= $$HOME/ktools/homesec
include ../../etc/Makefile-common

SHELL := /bin/bash

# ---------- custom targets

install: check_kcore_installed install-stamp

install-stamp: $(PLAIN_TARGETS)
	mkdir --mode 755 -p $(INSTALL_DIR)
	$(MAKE) common_install
	cp -pr --dereference $(SUBDIRS_TO_COPY) $(INSTALL_DIR)

$(TEST_LOG): $(wildcard *.py tests/*.py)
	script -e -c "pytest-3 tests" $(TEST_LOG)


# ---------- pass-throughs

clean: common_clean
	rm -rf private.d/__pycache__

comp: common_comp

test: check_kcore_installed common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)

