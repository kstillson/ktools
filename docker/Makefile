
# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := d-cowscan d-run
SH_TARGETS := d
PLAIN_TARGETS := d-common-opts.sh d-common.sh d_lib.py   # Listed here to preserve extension.
include ../common/Makefile-inc

# NB: tests the .py files in the current dir, not the files in STAGING_DIR.
# Doesn't depend on "all", and can be run independently (unusual for a Makefile).
# uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(STAGING_DIR)
	# script -c "pytest-3 test_*.py" $(TEST_LOG)

