
# Supported meta-targets:  all, clean, test, install, update

# Set default target before anything else in included...
all: common_all

# ----------

SHELL := /bin/bash

PY_TARGETS := procmon
CUSTOM_TARGETS := procmon_whitelist
PLAIN_TARGETS := procmon_wl_type.py   # PLAIN to preserve .py suffix (needed for importing)

USER := $(shell whoami)
INSTALL_DIR ?= $$HOME/ktools/procmon
include ../../etc/Makefile-common

SHELL := /bin/bash

# ---------- custom targets

WHITELIST_SOURCE := $(shell ls procmon_whitelist.py* private.d/procmon_whitelist.py* 2>/dev/null | head -1)
$(info $(WHITELIST_SOURCE))

$(INSTALL_DIR)/procmon_whitelist: $(WHITELIST_SOURCE)
	cp $(WHITELIST_SOURCE) $@
	chgrp procmon $@

$(TEST_LOG): $(wildcard *.py tests/*.py)
	set -o pipefail && python3 procmon_whitelist.py |& tee $(TEST_LOG)
	set -o pipefail && if [[ -f private.d/procmon_whitelist.py ]]; then PYTHONPATH=. python3 private.d/procmon_whitelist.py |& tee $(TEST_LOG); fi
	./procmon.py --logfile - --nocontainers --nocow --nodmap --nodupchk --noro --output '' --queue '' --test --whitelist tests/procmon_whitelist_allow_any.py |& fgrep -v Skipping |& tee $(TEST_LOG)
	@fgrep "all ok" $(TEST_LOG)


# ---------- pass-throughs

clean: common_clean

comp: common_comp

install: check_kcore_installed common_install

test: check_kcore_installed common_test

update: common_update

uninstall: common_uninstall
	rm -rf $(INSTALL_DIR)
