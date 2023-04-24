
all: copy docker-all

include ../../etc/Makefile-docker
include ../../etc/Makefile-common  # for $PLIB

KTOOLS_DIR ?= $(PLIB)/ktools

HSH_DIR := files/home/hs
HSH_FILES := controller.py data.py ext.py homesec.py model.py reset_dynamic_data.py view.py static templates
HSH_TARGETS := $(addprefix $(HSH_DIR)/, $(HSH_FILES))

PRIV_FILES := kcore_auth_db.data.pcrypt keymaster.crt
PRIV_TARGETS := $(addprefix $(HSH_DIR)/, $(PRIV_FILES))

HSH_PRIV_DIR := files/home/hs/private.d
PRIV_HS_FILES := data.py
PRIV_HS_TARGETS := $(addprefix $(HSH_PRIV_DIR)/, $(PRIV_HS_FILES))

KMH_TEST_FILES := kcore_auth_db-test.data.pcrypt km-test.data.pcrypt 
KMH_TEST_TARGETS := $(addprefix $(HSH_DIR)/, $(KMH_TEST_FILES))

KTOOLS_FILES := kmc.py ratelimiter.py
KTOOLS_TARGETS := $(addprefix $(KTOOLS_DIR)/, $(KTOOLS_FILES))

KTOOLS_ETC_FILES := pb-push.sh
KTOOLS_ETC_TARGETS := $(addprefix $(KTOOLS_DIR)/, $(KTOOLS_ETC_FILES))

DIRS := $(HSH_DIR) $(HSH_PRIV_DIR) $(KTOOLS_DIR)

# ---------- local custom logic

clean:
	rm -rf $(HSH_DIR) $(KTOOLS_DIR)

copy: $(DIRS) $(HSH_DIR) $(PRIV_TARGETS) $(PRIV_HS_DIR) $(PRIV_HS_TARGETS) $(HSH_TARGETS) $(KTOOLS_DIR) $(KTOOLS_TARGETS) $(KTOOLS_ETC_TARGETS)

$(DIRS):
	mkdir -m 0755 -p $@

$(HSH_TARGETS): $(HSH_DIR)/% : ../../services/homesec/%
	cp -r $^ $@
	chmod -R go+rX $@

$(PRIV_TARGETS): $(HSH_DIR)/% : ../../private.d/%
	install $^ $@

$(PRIV_HS_TARGETS): $(HSH_PRIV_DIR)/% : ../../services/homesec/private.d/%
	install $^ $@

$(KMH_TEST_TARGETS): $(HSH_DIR)/% : ../../services/keymaster/tests/%
	install $^ $@

$(KTOOLS_TARGETS): $(KTOOLS_DIR)/% : ../../pylib/tools/%
	install $^ $@

$(KTOOLS_ETC_TARGETS): $(KTOOLS_DIR)/% : ../../tools-etc/%
	install $^ $@

# ---------- pass-throughs

comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
