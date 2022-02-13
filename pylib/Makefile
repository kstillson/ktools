
# Supported meta-targets:  all, clean, test, install, update

# See install target, below.
INSTALL_DIR ?= "/tmp/tmp-install"
INSTALL_DIRS = $(shell ls -1d /usr/local/lib/python*/dist-packages)

PLAIN_TARGETS := k_common.py
include ../common/Makefile-inc

# NB: tests the .py files in the current dir, not the files in STAGING_DIR.
# Doesn't depend on "all", and can be run independently (unusual for a Makefile).
# uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard *.sh) $(STAGING_DIR)
	script -eq -c "pytest-3 test_*.py" $(TEST_LOG)
	script -eq -c "pytest test_*.py" $(TEST_LOG)

# The primary install target in common will install a throw-away copy of
# our files in /tmp/tmp-install.  But the real install logic follows.  We
# loop through all the Python dirs discovered in INSTALL_DIRS (above), and
# install the library into each of them.  Then we clean up the tmp.  We use
# the "install_real" target rather than "install" to prevent recursion.
install:
	for d in $(INSTALL_DIRS); do INSTALL_DIR=$$d $(MAKE) install_real; done
	rm -rf /tmp/tmp-install
