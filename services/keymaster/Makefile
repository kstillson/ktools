
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

PLAIN_TARGETS := $(wildcard *.py)

USER := $(shell whoami)
ifeq ($(USER),root)
	INSTALL_DIR := /usr/local/ktools/keymaster
else
	INSTALL_DIR := $$HOME/ktools/keymaster
endif
include ../../etc/Makefile-unstaged

SHELL := /bin/bash

# ---------- custom targets

$(TEST_LOG): $(wildcard *.py tests/*.py)
	script -e -c "pytest-3 tests" $(TEST_LOG)


# ---------- pass-throughs

clean: common_clean

comp: common_comp

install: common_install

test: common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)
