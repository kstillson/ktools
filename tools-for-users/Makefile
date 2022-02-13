
# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := ratelimiter run_para
SH_TARGETS := kmc pb-push
INSTALL_DIR := /usr/local/bin
include ../common/Makefile-unstaged

# ---------- testing

# uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard *.sh) $(STAGING_DIR)
	script -eq -c "pytest-3 test_*.py" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

comp: common_comp

clean: common_clean

install: common_install

test: common_test

uninstall: common_uninstall

upgrade: common_update
