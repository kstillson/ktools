
# NOTE: most of these targets depend on ../pylib/kcore/docker_lib,
# which should be installed before trying to get any of these to work.

all: common_all

# ----------

# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := d-cowscan d-run
SH_TARGETS := d d-build d-map
CUSTOM_TARGETS := d-cowscan.ignore
include ../etc/Makefile-common

# ---------- addl files

$(INSTALL_DIR)/d-cowscan.ignore: private.d/d-cowscan.ignore
	cp $^ $@

private.d/d-cowscan.ignore:
	touch $@

# ---------- testing

$(TEST_LOG): $(wildcard *.py) $(STAGING_DIR)
	script -e -c "pytest-3 tests" $(TEST_LOG)
	touch $(TEST_LOG)

# ---------- pass-throughs

comp:
	$(MAKE) common_comp

clean: common_clean
	rm -rf private.d/__pycache__*

install: check_kcore_installed
	$(MAKE) common_install

test: common_test

uninstall:
	$(MAKE) common_uninstall

update: common_update
