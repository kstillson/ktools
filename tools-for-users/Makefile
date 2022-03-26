
# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := kmc ratelimiter run_para
SH_TARGETS := pb-push
INSTALL_DIR := /usr/local/bin
include ../common/Makefile-unstaged

# ---------- testing

# uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard tests/*.py) $(wildcard *.sh) $(STAGING_DIR)
	script -eq -c "pytest-3 tests/test_*.py" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

comp: common_comp

clean: common_clean

install: common_install

test: common_test

uninstall: common_uninstall

update: common_update

# ---------- specialized local logic

KM_CERT_SOURCE := "../docker-containers/keymaster/private.d/server.crt"

# If you get the message
#
# make: *** No rule to make target '"../docker-containers/keymaster/private.d/server.crt"', needed by 'km.crt'.  Stop.
#
# here's the problem: the keymaster uses a self-signed certificate for TLS.
# The client needs that cert to check the connection, but it looks like you
# haven't generated it yet.  To fix that, run:
# cd ../docker-containers/keymaster; bash ./Build
#
# This Makefile doesn't try to do that for you because you actually need to
# set some settings before the cert can be generated.  When you run the build
# script, it'll explain how to set the settings.  Once your cert is generated,
# you can come back here and run the make again.

km.crt: $(KM_CERT_SOURCE)
	install $^ $@

$(KM_CERT_SOURCE):

