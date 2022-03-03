
# Actual list of target install dirs.
INSTALL_DIRS = $(shell ls -1d /usr/local/lib/python*/dist-packages)

# Marked as PLAIN rather than PY targets to preserve the extension.
PLAIN_TARGETS := $(wildcard *.py)
include ../common/Makefile-unstaged

# ---------- testing

# Test everything under both python 2 & 3.
# Uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard tests/*.py)
	script -eq -c "pytest-3 tests/test_*.py" $(TEST_LOG)
	script -a -eq -c "pytest tests/test_*.py" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

clean: common_clean

test: common_test

update: common_update

# ---------- local custom locic

comp: FORCE
	INSTALL_DIR=$(shell ls -1d /usr/local/lib/python*/dist-packages | head -1) $(MAKE) --no-print-directory common_comp

install:
	for d in $(INSTALL_DIRS); do INSTALL_DIR=$$d $(MAKE) --no-print-directory common_install; done

uninstall:
	for d in $(INSTALL_DIRS); do cd $$d; rm $(PLAIN_TARGETS); done
