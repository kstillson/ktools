
HSH_DIR := files/home/hs
HSH_FILES := controller.py data.py ext.py homesec.py model.py reset_dynamic_data.py view.py static templates
HSH_TARGETS := $(addprefix $(HSH_DIR)/, $(HSH_FILES))

PRIV_FILES := kcore_auth_db.data.gpg keymaster.crt
PRIV_TARGETS := $(addprefix $(HSH_DIR)/, $(PRIV_FILES))

KMH_TEST_FILES := kcore_auth_db-test.data.gpg km-test.data.gpg 
KMH_TEST_TARGETS := $(addprefix $(HSH_DIR)/, $(KMH_TEST_FILES))

KCORE_DIR := files/usr/lib/python3.9/site-packages/kcore
KCORE_FILES := auth.py common.py html.py uncommon.py varz.py webserver.py
KCORE_TARGETS := $(addprefix $(KCORE_DIR)/, $(KCORE_FILES))

KTOOLS_DIR := files/usr/lib/python3.9/site-packages/ktools
KTOOLS_FILES := kmc.py
KTOOLS_TARGETS := $(addprefix $(KTOOLS_DIR)/, $(KTOOLS_FILES))

DIRS := $(HSH_DIR) $(KCORE_DIR) $(KTOOLS_DIR)

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(HSH_DIR) $(KCORE_DIR) $(KTOOLS_DIR)

copy: $(DIRS) $(HSH_DIR) $(PRIV_TARGETS) $(HSH_TARGETS) $(KCORE_DIR) $(KCORE_TARGETS) $(KTOOLS_DIR) $(KTOOLS_TARGETS)

$(DIRS):
	mkdir -p $@

$(HSH_TARGETS): $(HSH_DIR)/% : ../../services/homesec/%
	cp -r $^ $@

$(PRIV_TARGETS): $(HSH_DIR)/% : ../../private.d/%
	cp $^ $@

$(KMH_TEST_TARGETS): $(HSH_DIR)/% : ../../services/keymaster/tests/%
	cp $^ $@

$(KCORE_TARGETS): $(KCORE_DIR)/% : ../../pylib/kcore/%
	cp $^ $@

$(KTOOLS_TARGETS): $(KTOOLS_DIR)/% : ../../pylib/tools/%
	cp $^ $@

# ---------- pass-throughs

include ../../common/Makefile-docker
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
