
# NOTE: most of these targets depend on ../pylib/kcore/docker_lib,
# which should be installed before trying to get any of these to work.

all: common_all

# ----------

# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := d-cowscan d-run
SH_TARGETS := d d-build d-map
# only useful by and for root:
INSTALL_DIR ?= /root/bin
include ../etc/Makefile-common

# ---------- addl files

install: $(INSTALL_DIR)/d-cowscan.ignore

$(INSTALL_DIR)/d-cowscan.ignore: private.d/d-cowscan.ignore
	sudo cp $^ $@


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
	@echo "about to sudo for docker-infrastructure:comp -- these had to be installed by root, and generally permissions now need root to read(/compare) them."
	sudo $(MAKE) common_comp

clean: common_clean
	rm -rf private.d/__pycache__*

install: check_kcore_installed
	@echo "about to sudo for docker-infrastructure:install -- these tools can only be used by root, so it is assumed you want to install them where root can use them."
	sudo $(MAKE) common_install

test: common_test

uninstall:
	@echo "about to sudo for docker-infrastructure:install -- these were installed for root by sudo, and so must be uninstalled that way."
	sudo $(MAKE) common_uninstall

update: common_update
