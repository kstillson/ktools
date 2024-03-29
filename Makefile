
# See ./Readme-makefiles.md for details

# Control variables inherited from the environment:
#   BUILD_DOCKER_CONTAINERS
#   NO_TRACKING
#   SUBDIRS

TOP_TARGETS = all clean comp install test uninstall update
SUBDIRS ?= pylib tools-etc tools-for-root services container-infrastructure

ifeq ($(BUILD_DOCKER_CONTAINERS), 1)
  SUBDIRS := $(SUBDIRS) containers
endif

SHELL := /bin/bash
include etc/Makefile-colors

# ---------- standard targets

# Because it's first, this is the default target.
# Note that the $(TOP_TARGETS) rule below this one also inclueds "all".
# Both rules will run..  So we do the local :prep receipe first, and then echo "all" into the subdirs.
#
all:	prep
	@if [[ "$$BUILD_DOCKER_CONTAINERS" != "1" ]]; then printf "\n  $(YELLOW)NOTE: $(RESET) containers/... not included in the build.\n         If you think you want it, check README.md and then set 'BUILD_DOCKER_CONTAINERS=1'.\n\n"; fi

# This also includes "all"; both rules will run.
$(TOP_TARGETS): $(SUBDIRS)

$(SUBDIRS):
	@printf "\nstarting subdir $(GREEN) $@ $(RESET)\n"
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

# ---------- special additions to common targets

clean:
	rm -rf home-control/__pycache__ etc/prep-stamp .pytest_cache
	@printf "\n  NOT cleaning $(YELLOW)private.d/$(RESET) as can contain valuable data modified outside of make.  remove manually if you're sure.\n\n"


# ---------- 1-time preparation sequence

prep:	etc/prep-stamp

etc/prep-stamp:	private.d private.d/kcore_auth_db.data.pcrypt private.d/keymaster.pem private.d/wifi_secrets.py services/homesec/private.d/data.py $${HOME}/.ktools.settings
	etc/check-package-deps.sh
	if [[ -z "$$NO_TRACKING" ]]; then etc/tracking.sh "$@"; fi
	touch etc/prep-stamp

private.d:
	mkdir -p $@
	# Create the subdir tree within private.d expected by the various private.d symlinks.
	mkdir -p $(shell find . -type l | egrep "private.d$$" | sed -e "s:/private.d::" -e "s/^\./private.d/")

private.d/kcore_auth_db.data.pcrypt:
	touch $@

private.d/keymaster.pem:   private.d/cert-settings
	@if [[ -f private.d/keymaster.key ]]; then printf "\n$(RED)ERROR $(RESET) dont want to overwrite private.d/keymaster.key, although private.d/cert-settings apears to be more recent.\nPlease manually remove 'private.d/key*' if it really is time to generate a new key,\nor run 'touch private.d/keymaster.pem' to keep your current keys and move on.\n\n"; exit 2; fi
	source private.d/cert-settings && \
	  openssl req -x509 -newkey rsa:4096 -days $$DAYS \
	    -keyout private.d/keymaster.key -out private.d/keymaster.crt -nodes \
	    -subj "$${SUBJECT}/CN=$${KM_HOSTNAME}/emailAddress=$${EMAIL}" \
	    -addext "subjectAltName = DNS:$${KM_HOSTNAME}"
	cat private.d/keymaster.crt private.d/keymaster.key > private.d/keymaster.pem
	chmod go+r private.d/keymaster.crt
	chmod go-r private.d/keymaster.key private.d/keymaster.pem

private.d/cert-settings:
	mkdir -p private.d
	cp -n etc/cert-settings.template private.d/cert-settings
	editor private.d/cert-settings

private.d/wifi_secrets.py:
	cp -n etc/wifi_secrets.template private.d/wifi_secrets.py
	editor private.d/wifi_secrets.py

services/homesec/private.d/data.py:
	mkdir -p $(shell dirname $@)
	touch $@

$${HOME}/.ktools.settings: etc/initial-ktools.settings
	cp -nv $^ $@
