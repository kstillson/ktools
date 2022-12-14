
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


# ----- Create an empty private.d/d-cowscan.ignore if one doesn't exist.

private.d/d-cowscan.ignore:  private.d
	touch $@

private.d:
	mkdir -p $@


# ---------- testing

# TODO: add some tests
$(TEST_LOG): $(wildcard *.py) $(STAGING_DIR)
	touch $(TEST_LOG)
	# script -e -c "pytest-3 test_*.py" $(TEST_LOG)

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
