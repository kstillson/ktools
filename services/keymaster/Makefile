
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

PLAIN_TARGETS := $(wildcard *.py)

USER := $(shell whoami)
INSTALL_DIR := $$HOME/ktools/keymaster
include ../../etc/Makefile-common

SHELL := /bin/bash

# ---------- custom targets

$(TEST_LOG): $(wildcard *.py tests/*.py)
	script -e -c "pytest-3 tests" $(TEST_LOG)


# ---------- pass-throughs

clean: common_clean

comp: common_comp

install: check_kcore_installed common_install

test: check_kcore_installed common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)
