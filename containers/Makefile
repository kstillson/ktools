TOP_TARGETS = all clean install promote push test update
SHELL := /bin/bash

all: prep

include ../etc/Makefile-colors
##include ../etc/Makefile-docker

# WARNING- all docker containers (except kcore-baseline) depend on
# kcore-baseline being built AND INSTALLED (i.e. marked :live) before the
# other containers can be BUILT.
#
# For this reason, kcore-baseline is listed first here, and the :all target
# for kcore-baseline will BUILD, test AND INSTALL.
#
SUBDIRS ?= kcore-baseline $(shell ls */Makefile | cut -d/ -f1 | fgrep -v kcore-baseline)

# This also includes "all"; both rules will run.
$(TOP_TARGETS): $(SUBDIRS)

$(SUBDIRS):
	@printf "\nstarting subdir $(GREEN) $@ $(RESET)\n"
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)


# ---------- special additions to common targets

clean:
	rm -f prep-stamp
	@printf "\nuse '$(YELLOW)make purge$(RESET)' if you also want to remove all built Docker images\n\n"


# ---------- custom targets

purge:
	@read -p 'About to purge ALL docker images (not just the ones created by this Makefile). ok (y/n)? ' ok && if [[ "$$ok" == "y" ]]; then sudo -E $(DOCKER_EXEC) image prune -a; else exit -1; fi


# ---------- 1-time preparation sequence

prep:  prep-stamp

prep-stamp:
	../etc/check-package-deps.sh docker
	python3 -m kcore.docker_lib || { echo ""; read -p "kcore/pylib needs to be installed for user/$$USER so tests can be run via kcore.docker_lib.  okay to do that now (y/n)? " ok && if [[ "$$ok" == "y" ]]; then SUBDIRS=pylib make -C .. install; else exit -1; fi; }
	if [[ "$(NEED_SUDO)" == "1" ]]; then $(MAKE) prep-stamp-root; fi
	touch prep-stamp

prep-stamp-root:
	sudo ls /root/bin/d-build || { echo ""; read -p 'parts of kcore *also* needs to be installed for user/root to build docker containers.  okay to do that now (y/n)? ' ok && if [[ "$$ok" == "y" ]]; then sudo -E SUBDIRS="pylib container-infrastructure" make -C .. install; else exit -1; fi; }
	sudo -E docker network rm docker2 >&/dev/null || true
	sudo -E docker network create -d bridge --gateway 192.168.3.1 --subnet 192.168.3.0/24 --opt com.docker.network.bridge.name=docker2 docker2
