
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
	mkdir --parents --mode=750 $@
	if [[ "$UID" == "0" ]]; then \
	    chown ${UID_OUTSIDE}:${GID_OUTSIDE} $@
	else
	    @printf "\n$(YELLOW) WARNING $(RESET)- not root, so cant fix ownership on volume dirs.  owner should be ${UID_OUTSIDE}:${GID_OUTSIDE} for ${VOL_DIRS}\n\n"
	fi


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
