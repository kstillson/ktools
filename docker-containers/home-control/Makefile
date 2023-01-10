
all: copy docker-all

include ../../etc/Makefile-docker

HCH_DIR := files/home/hc
HCH_FILES := home_control_service.py root.html
HCH_TARGETS := $(addprefix $(HCH_DIR)/, $(HCH_FILES))

PLIB_DIR := $(PLIB)/home_control
PLIB_FILES := hc.py hcdata_devices.py hcdata_scenes.py hcdata_test_device.py plugin_delay.py plugin_test.py plugin_tplink.py plugin_web.py
PLIB_TARGETS := $(addprefix $(PLIB_DIR)/, $(PLIB_FILES))

DIRS := $(HCH_DIR) $(PLIB_DIR)

# ---------- local custom logic

clean:
	rm -rf $(HCH_DIR) $(PLIB_DIR)

copy: $(DIRS) $(HCH_DIR) $(HCH_TARGETS) $(PLIB_DIR) $(PLIB_TARGETS)

$(DIRS):
	mkdir -p $@

$(HCH_TARGETS): $(HCH_DIR)/% : ../../services/home-control/%
	cp $^ $@

$(PLIB_TARGETS): $(PLIB_DIR)/% : ../../pylib/home_control/%
	cp $^ $@


# ---------- pass-throughs

comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
