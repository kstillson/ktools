
# ---------- custom default target
# (needs to be before including Makefile-docker)

all:	vol_dirs docker-all

# ---------- control variables

UID_SEARCH ?= nagios   # causes $(UID_OUTSIDE) to be set.
GID_SEARCH ?= nagios   # causes $(GID_OUTSIDE) to be set.

include ../../etc/Makefile-docker

VOLS ?= $(DOCKER_VOLS)/nagdock
VN := $(VOLS)/var_nagios
VOL_DIRS := $(VOLS)/var_log_nagios $(VN) $(VN)/archive $(VN)/rw $(VN)/spool $(VN)/spool/checkresults


# ---------- custom logic for "all"

vol_dirs: ${VOL_DIRS}

${VOL_DIRS}:
	sudo mkdir --parents --mode=755 $@
	sudo chown ${UID_OUTSIDE}:${GID_OUTSIDE} $@


# ---------- pass-throughs


comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
