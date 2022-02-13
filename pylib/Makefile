
# Supported meta-targets:  all, clean, test, install, update

INSTALL_DIR = "/usr/local/lib/python3.8/dist-packages"

PLAIN_TARGETS := k_common.py
include ../common/Makefile-inc

# NB: tests the .py files in the current dir, not the files in STAGING_DIR.
# Doesn't depend on "all", and can be run independently (unusual for a Makefile).
# uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard *.sh) $(STAGING_DIR)
	script -eq -c "pytest-3 test_*.py" $(TEST_LOG)
	script -eq -c "pytest test_*.py" $(TEST_LOG)

