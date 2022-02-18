
# TODO: install should really just install circuitpy-sim in the local site libs

# TODO: add install-hw that puts the libaries onto real hardware and test-hw that tests it there.

# TODO: k_common


# Actual list of target install dirs.
INSTALL_BASE_DIRS = $(shell ls -1d /usr/local/lib/python*/dist-packages)
INSTALL_DIRS = $(patsubst %, %/circuitpy_lib, $(INSTALL_BASE_DIRS))

# Marked as PLAIN rather than PY targets to preserve the extension.
PLAIN_TARGETS := $(wildcard *.py)
include ../common/Makefile-unstaged

# ---------- testing

# Test everything under both python 2 & 3.
# Uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py)
	script -eq -c "pytest-3 tests/test_*.py" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

test: common_test

update: common_update

# ---------- local custom locic

clean:
	$(MAKE) --no-print-directory common_clean
	rm -rf circuitpy_sim/__pycache__ circuitpy_sim/*.pyc

comp: FORCE
	INSTALL_DIR=$(shell ls -1d /usr/local/lib/python*/dist-packages | head -1) $(MAKE) --no-print-directory common_comp

install:
	for d in $(INSTALL_DIRS); do mkdir -p $$d; INSTALL_DIR=$$d $(MAKE) --no-print-directory common_install; done

uninstall:
	for d in $(INSTALL_DIRS); do cd $$d; rm $(PLAIN_TARGETS); rmdir $$d; done
