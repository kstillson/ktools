
# Actual list of target install dirs.
# NB: Adafruit only supports py3, so limiting installs to py3 lib dirs.
BASE_DIRS = $(shell ls -1d /usr/local/lib/python3*/dist-packages)
INSTALL_DIRS = $(patsubst %,%/circuitpy_sim,$(BASE_DIRS))

# TODO: need to include subdirs (e.g. adafruit_esp32spi) and their contents.

# Marked as PLAIN rather than PY targets to preserve the extension.
PLAIN_TARGETS := $(wildcard *.py)
include ../common/Makefile-unstaged

# ---------- testing

# Uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py)
	script -eq -c "pytest-3 tests/test_*.py" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

clean: common_clean

test: common_test

update: common_update

# ---------- local custom locic

comp: FORCE
	for d in $(INSTALL_DIRS); do INSTALL_DIR=$$d $(MAKE) --no-print-directory common_comp; done

install:
	for d in $(INSTALL_DIRS); do mkdir -p $$d; INSTALL_DIR=$$d $(MAKE) --no-print-directory common_install; done

uninstall:
	for d in $(INSTALL_DIRS); do cd $$d; rm $(PLAIN_TARGETS); rmdir $$d; done
