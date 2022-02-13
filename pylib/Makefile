
# Supported meta-targets:  all, clean, test, install, update
# Supported regular targets: uninstall

# See install target, below.
INSTALL_DIR ?= "/tmp"
INSTALL_DIRS = $(shell ls -1d /usr/local/lib/python*/dist-packages)

# Marked as PLAIN rather than PY targets to preserve the extension.
PLAIN_TARGETS := k_auth.py k_common.py k_gpio.py k_html.py k_varz.py k_webserver.py
include ../common/Makefile-inc

# NB: tests the .py files in the current dir, not the files in STAGING_DIR.
# Doesn't depend on "all", and can be run independently (unusual for a Makefile).
# Uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard *.sh) $(STAGING_DIR)
	script -eq -c "pytest-3 test_*.py" $(TEST_LOG)
	script -eq -c "pytest test_*.py" $(TEST_LOG)

# Not sure why this doesn't override the install target in Makefile-inc,
# but it seems that instead both recipies run.  So- we'll have the one from
# Makefile-inc install a throw-away copy into /tmp, and then the real
# install logic (below) loops through all active Python site library
# directories and installs our libs into each.  We use the "install_real"
# target rather than "install" to prevent recursion.
install:
	for d in $(INSTALL_DIRS); do INSTALL_DIR=$$d $(MAKE) install_real; done
	cd /tmp; rm -f $(PLAIN_TARGETS)

# This overrides the default recipe in ../common/Makefile.inc
# make might generate a warning; ignore it.
uninstall:
	for d in $(INSTALL_DIRS); do cd $$d; rm $(PLAIN_TARGETS); done
