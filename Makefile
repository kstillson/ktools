
# See ./Readme-makefiles.md

TOP_TARGETS = all clean comp install test uninstall update
SUBDIRS ?= pylib tools-for-root services docker-infrastructure

ifeq ($(BUILD_DOCKER_CONTAINERS), 1)
  SUBDIRS := $(SUBDIRS) docker-containers
endif

SHELL := /bin/bash
include etc/Makefile-colors

# ---------- standard targets

all:	prep
	@if [[ "$$BUILD_DOCKER_CONTAINERS" != "1" ]]; then printf "\n  $(YELLOW)NOTE: $(RESET) docker-containers/... not included in the build.\n         If you think you want it, check README.md and then set 'BUILD_DOCKER_CONTAINERS=1'.\n\n"; fi

# This also includes "all"; both rules will run.
$(TOP_TARGETS): $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

# ---------- special additions to common targets

clean:
	rm -rf home-control/__pycache__ etc/prep-stamp .pytest_cache
	@printf "\n  NOT cleaning $(YELLOW)private.d/$(RESET) as can contain valuable data modified outside of make.  remove manually if you're sure.\n\n"


# ---------- 1-time preparation sequence

prep:	etc/prep-stamp

etc/prep-stamp:	private.d/kcore_auth_db.data.pcrypt private.d/keymaster.pem private.d/wifi_secrets.py services/homesec/private.d/data.py
	etc/check-package-deps.sh
	touch etc/prep-stamp

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

