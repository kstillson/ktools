
KMH_DIR := files/home/km
KMH_FILES := km.py
KMH_TARGETS := $(addprefix $(KMH_DIR)/, $(KMH_FILES))

KMH_TEST_FILES := kcore_auth_db-test.data.pcrypt km-test.data.pcrypt
KMH_TEST_TARGETS := $(addprefix $(KMH_DIR)/, $(KMH_TEST_FILES))

PRIV_FILES := kcore_auth_db.data.pcrypt keymaster.pem km.data.pcrypt
PRIV_TARGETS := $(addprefix $(KMH_DIR)/, $(PRIV_FILES))

DIRS := $(KMH_DIR) $(KMH_DIR)/.gnupg

SHELL :=/bin/bash

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(KMH_DIR)

restart: docker-update
	if [[ "$$p" == "" ]]; then read -s -p "km password for startup: " p; else sleep 1; fi && echo "" && d 01 keymaster && sleep 2 && curl --cacert files/home/km/keymaster.pem -d "password=$$p" https://keys:4444/load

# ----- file copies

copy: $(DIRS) $(KMH_DIR) $(KMH_TARGETS) $(KMH_TEST_TARGETS) $(PRIV_TARGETS)

$(DIRS):
	mkdir -p $@

$(KMH_TARGETS): $(KMH_DIR)/% : ../../services/keymaster/%
	cp -p $^ $@

$(KMH_TEST_TARGETS): $(KMH_DIR)/% : ../../services/keymaster/tests/%
	cp -p $^ $@

$(PRIV_TARGETS): $(KMH_DIR)/% : ../../private.d/%
	cp -p $^ $@

# -----

../../private.d/km.data.pcrypt: ../../services/keymaster/tests/km-test.data.pcrypt
	# Only copy template file if target doesn't exist, regardless of which is newer.
	if [[ ! -f $@ ]]; then echo "COULD NOT FIND $@, SO USING $^ AS A STARTING POINT"; cp -p $^ $@; fi


# ---------- pass-throughs

include ../../etc/Makefile-docker
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
