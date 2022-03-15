
# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := d-cowscan d-run
SH_TARGETS := d d-build d-map
PLAIN_TARGETS := d_lib.py	 # Listed here to preserve extension.
include ../common/Makefile-unstaged

# ---------- testing

# TODO: add some tests
$(TEST_LOG): $(wildcard *.py) $(STAGING_DIR)
	touch $(TEST_LOG)
	# script -c "pytest-3 test_*.py" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

comp: common_comp

clean: common_clean

install: common_install

test: common_test

uninstall: common_uninstall

update: common_update
