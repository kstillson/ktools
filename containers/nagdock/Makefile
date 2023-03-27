
# ---------- default target
# (needs to be before including Makefile-docker)

all:	docker-all

# ---------- control variables

DOCKER_EXEC ?= $(shell ktools_settings -b docker_exec)

UID_SEARCH ?= nagios   # causes $(UID_OUTSIDE) to be set by Makefile-docker.
GID_SEARCH ?= nagios   # causes $(GID_OUTSIDE) to be set by Makefile-docker.

include ../../etc/Makefile-docker

VOLS ?= $(DOCKER_VOLS)/nagdock
VN := $(VOLS)/var_nagios
VOL_DIRS := $(VOLS)/var_log_nagios $(VN) $(VN)/archive $(VN)/rw $(VN)/spool $(VN)/spool/checkresults


# ---------- custom logic for "all"

vol_dirs: ${VOL_DIRS}
	@if [[ "$$UID" == "0" ]]; then \
	    chown ${UID_OUTSIDE}:${GID_OUTSIDE} ${VOL_DIRS}; \
	elif [[ "$DOCKER_EXEC" == *"podman" ]]; then \
	    $DOCKER_EXEC unshare chown ${UID_INSIDE}:${GID_INSIDE} ${VOL_DIRS}; \
	else \
	    printf "\n$(YELLOW) WARNING $(RESET)- not root, so cant fix ownership on volume dirs.  owner should be ${UID_OUTSIDE}:${GID_OUTSIDE} for ${VOL_DIRS}\n\n"; \
	fi

${VOL_DIRS}:
	mkdir --parents --mode=755 $@


# ---------- other custom targets

test: vol_dirs docker-test


# ---------- pass-throughs

comp:  # n/a
clean: docker-clean
install: docker-install
uninstall: docker-uninstall
update: docker-update
