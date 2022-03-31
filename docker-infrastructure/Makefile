
# NOTE: most of these targets depend on ../pylib/kcore/docker_lib,
# which should be installed before trying to get any of these to work.

# ----------

# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := d-cowscan d-run
SH_TARGETS := d d-build d-map
include ../common/Makefile-unstaged

# ---------- testing

# TODO: add some tests
$(TEST_LOG): $(wildcard *.py) $(STAGING_DIR)
	touch $(TEST_LOG)
	# script -e -c "pytest-3 test_*.py" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

comp: common_comp

clean: common_clean

install:
	sudo $(MAKE) common_install

test: common_test

uninstall:
	sudo $(MAKE) common_uninstall

update: common_update
