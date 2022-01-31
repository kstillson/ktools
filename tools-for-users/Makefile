
# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := ratelimiter run_para
SH_TARGETS := pb-push
include ../../common/Makefile-inc

# NB: tests the .py files in the current dir, not the files in STAGING_DIR.
# Doesn't depend on "all", and can be run independently (unusual for a Makefile).
# uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard *.sh) $(STAGING_DIR)
	script -eq -c "pytest-3 test_*.py" $(TEST_LOG)

