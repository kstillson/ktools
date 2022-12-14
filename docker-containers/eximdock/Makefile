
# ---------- default target
# (needs to be before including Makefile-docker)

all: docker-all


# ---------- control variables

UID_SEARCH ?= exim   # causes $(UID_OUTSIDE) to be set.
GID_SEARCH ?= exim   # causes $(GID_OUTSIDE) to be set.

include ../../etc/Makefile-docker

VOLS ?= ${DOCKER_VOLS}/eximdock
VOL_DIRS := ${VOLS}/var_log/exim ${VOLS}/var_mail ${VOLS}/var_spool/exim/db ${VOLS}/var_spool/exim/input ${VOLS}/var_spool/exim/msglog

CONF_PRIV_DIR ?= files/etc/exim/private.d
CONF_PRIV ?= $(shell ls -ald $(CONF_PRIV_DIR))


# ---------- custom logic for "all"

vol_dirs: ${VOL_DIRS}

${VOL_DIRS}:
	sudo mkdir --parents --mode=750 $@
	sudo -E chown ${UID_OUTSIDE}:${GID_OUTSIDE} $@


# ---------- custom logic for testing

ifeq ($(CONF_PRIV),)
test:
	@echo "exim test bypassed because ${CONF_PRIV_DIR} not found"
else
test: vol_dirs docker-test
endif


# ---------- pass-throughs

clean: docker-clean
install: docker-install
uninstall: docker-uninstall
update: docker-update
