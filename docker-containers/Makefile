TOP_TARGETS = all clean install test update

SHELL := /bin/bash
include ../etc/Makefile-colors

# WARNING- all docker containers (except kcore-baseline) depend on
# kcore-baseline being built AND INSTALLED (i.e. marked :live) before the
# other containers can be BUILT.
#
# For this reason, kcore-baseline is listed first here, and the :all target
# for kcore-baseline will BUILD, test AND INSTALL.
#
SUBDIRS ?= kcore-baseline $(shell ls */Makefile | cut -d/ -f1 | fgrep -v kcore-baseline)

all: prep

# This also includes "all"; both rules will run.
$(TOP_TARGETS): $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)


# ---------- special additions to common targets

clean:
	rm -f prep-stamp
	@printf "\nuse '$(YELLOW)make purge$(RESET)' if you also want to remove all built Docker images\n\n"


# ---------- custom targets

purge:
	@read -p 'About to purge ALL docker images (not just the ones created by this Makefile). ok (y/n)? ' ok && if [[ "$$ok" == "y" ]]; then sudo docker image prune -a; else exit -1; fi


# ---------- 1-time preparation sequence

prep:  prep-stamp

prep-stamp:
	../etc/check-package-deps.sh docker
	sudo docker network rm docker2 >&/dev/null || true
	sudo docker network create -d bridge --gateway 192.168.3.1 --subnet 192.168.3.0/24 --opt com.docker.network.bridge.name=docker2 docker2
	touch prep-stamp

