
KMH_DIR := files/home/km
KMH_FILES := km.py
KMH_TARGETS := $(addprefix $(KMH_DIR)/, $(KMH_FILES))

KMH_TEST_FILES := kcore_auth_db-test.data.gpg km-test.data.gpg 
KMH_TEST_TARGETS := $(addprefix $(KMH_DIR)/, $(KMH_TEST_FILES))

PRIV_FILES := kcore_auth_db.data.gpg keymaster.pem km.data.gpg
PRIV_TARGETS := $(addprefix $(KMH_DIR)/, $(PRIV_FILES))

KCORE_DIR := files/usr/lib/python3.9/site-packages/kcore
KCORE_FILES := auth.py common.py html.py uncommon.py varz.py webserver.py webserver_base.py 
KCORE_TARGETS := $(addprefix $(KCORE_DIR)/, $(KCORE_FILES))

DIRS := $(KMH_DIR) $(KMH_DIR)/.gnupg $(KCORE_DIR) 

SHELL :=/bin/bash

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(KMH_DIR) $(KCORE_DIR)

restart: docker-update
	if [[ "$$p" == "" ]]; then read -s -p "km password for startup: " p; else sleep 1; fi && echo "" && d 01 keymaster && sleep 2 && curl --cacert files/home/km/keymaster.pem -d "password=$$p" https://keys:4444/load

# ----- file copies

copy: $(DIRS) $(KMH_DIR) $(KMH_TARGETS) $(KMH_TEST_TARGETS) $(PRIV_TARGETS) $(KCORE_DIR) $(KCORE_TARGETS)

$(DIRS):
	mkdir -p $@

$(KMH_TARGETS): $(KMH_DIR)/% : ../../services/keymaster/%
	cp -p $^ $@

$(KMH_TEST_TARGETS): $(KMH_DIR)/% : ../../services/keymaster/tests/%
	cp -p $^ $@

$(PRIV_TARGETS): $(KMH_DIR)/% : ../../private.d/%
	cp -p $^ $@

$(KCORE_TARGETS): $(KCORE_DIR)/% : ../../pylib/kcore/%
	cp -p $^ $@

# -----

../../private.d/km.data.gpg: ../../services/keymaster/tests/km-test.data.gpg
	@echo "COULD NOT FIND $@, SO USING $^ AS A STARTING POINT"
	cp -p $^ $@


# ---------- pass-throughs

include ../../common/Makefile-docker
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
