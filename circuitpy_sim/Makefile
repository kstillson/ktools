
# Actual list of target install dirs.
BASE_DIRS = $(shell ls -1d /usr/local/lib/python*/dist-packages)
INSTALL_DIRS = $(patsubst %,%/circuitpy_sim,$(BASE_DIRS))

# Marked as PLAIN rather than PY targets to preserve the extension.
PLAIN_TARGETS := adafruit_requests.py board.py circpysim_logging.py Makefile neopixel.py rtc.py socketpool.py wifi.py
include ../common/Makefile-unstaged

# ---------- testing

# Test everything under both python 2 & 3.
# Uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py)
	script -eq -c "pytest-3 test_*.py" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

clean: common_clean

test: common_test

update: common_update

# ---------- local custom locic

comp: FORCE
	INSTALL_DIR=$(shell ls -1d /usr/local/lib/python*/dist-packages | head -1) $(MAKE) --no-print-directory common_comp

install:
	for d in $(INSTALL_DIRS); do mkdir -p $$d; INSTALL_DIR=$$d $(MAKE) --no-print-directory common_install; done

uninstall:
	for d in $(INSTALL_DIRS); do cd $$d; rm $(PLAIN_TARGETS); rmdir $$d; done
