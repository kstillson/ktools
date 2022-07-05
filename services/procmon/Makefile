
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

SHELL := /bin/bash

PY_TARGETS := procmon procmon_whitelist
PLAIN_TARGETS := procmon_wl_type.py   # PLAIN to preserve .py suffix (needed for importing)

USER := $(shell whoami)
INSTALL_DIR ?= $$HOME/ktools/procmon
include ../../etc/Makefile-common

SHELL := /bin/bash

# ---------- custom targets

$(TEST_LOG): $(wildcard *.py tests/*.py)
	set -o pipefail && ./tests/procmon_test.sh |& tee $(TEST_LOG)


# ---------- pass-throughs

clean: common_clean

comp: common_comp

install: check_kcore_installed common_install

test: check_kcore_installed common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)
