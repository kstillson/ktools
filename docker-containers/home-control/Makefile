
HCH_DIR := files/home/hc
HCH_FILES := home_control_service.py root.html hcdata_devices.py hcdata_scenes.py hcdata_test_device.py
HCH_TARGETS := $(addprefix $(HCH_DIR)/, $(HCH_FILES))

PLIB_DIR := files/usr/lib/python3.9/site-packages/home_control
PLIB_FILES := hc.py plugin_delay.py plugin_test.py plugin_tplink.py plugin_web.py 
PLIB_TARGETS := $(addprefix $(PLIB_DIR)/, $(PLIB_FILES))

KCORE_DIR := files/usr/lib/python3.9/site-packages/kcore
KCORE_FILES := common.py html.py webserver_base.py webserver.py varz.py 
KCORE_TARGETS := $(addprefix $(KCORE_DIR)/, $(KCORE_FILES))

DIRS := $(HCH_DIR) $(PLIB_DIR) $(KCORE_DIR)

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(HCH_DIR) $(PLIB_DIR) $(KCORE_DIR)

copy: $(DIRS) $(HCH_DIR) $(HCH_TARGETS) $(PLIB_DIR) $(PLIB_TARGETS) $(KCORE_DIR) $(KCORE_TARGETS)

$(DIRS):
	mkdir -p $@

$(HCH_TARGETS): $(HCH_DIR)/% : ../../services/home-control/%
	cp $^ $@

$(PLIB_TARGETS): $(PLIB_DIR)/% : ../../pylib/home_control/%
	cp $^ $@

$(KCORE_TARGETS): $(KCORE_DIR)/% : ../../pylib/kcore/%
	cp $^ $@


# ---------- pass-throughs

include ../../common/Makefile-docker
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
