
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

SHELL := /bin/bash

PY_TARGETS := filewatch filewatch_config
INSTALL_DIR ?= $$HOME/ktools/filewatch
include ../../etc/Makefile-common

SHELL := /bin/bash

# ---------- custom targets

$(TEST_LOG): $(wildcard *.py tests/*.py)
	set -o pipefail && ./tests/filewatch_test.sh |& tee $(TEST_LOG)


# ---------- pass-throughs

clean: common_clean

comp: common_comp

install: check_kcore_installed common_install

test: check_kcore_installed common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)
