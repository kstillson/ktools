
HCH := files/home/hc
PLIB := files/usr/lib/python3.9/site-packages
COPIED_FILES := $(HCH)/home_control_service.py $(HCH)/root.html \
   $(HCH)/hcdata_devices.py $(HCH)/hcdata_scenes.py $(HCH)/hcdata_test_device.py  \
   $(PLIB)/hc.py $(PLIB)/plugin_delay.py $(PLIB)/plugin_test.py $(PLIB)/plugin_tplink.py $(PLIB)/plugin_web.py \
   $(PLIB)/kcore/varz.py


# ---------- local additions (remove files copied over by ./Build)

all:	$(COPIED_FILES)
	$(MAKE) docker-all

clean:
	rm -rf $(COPIED_FILES)

$(HCH)/home_control_service.py: ../../services/home-control/home_control_service.py
	cp $^ $@

$(HCH)/root.html: ../../services/home-control/root.html
	cp $^ $@

$(HCH)/hcdata_devices.py: ../../home-control/hcdata_devices.py
	cp $^ $@

$(HCH)/hcdata_scenes.py: ../../home-control/hcdata_scenes.py
	cp $^ $@

$(HCH)/hcdata_test_device.py: ../../home-control/hcdata_test_device.py
	cp $^ $@

$(PLIB)/hc.py: ../../pylib/home_control/hc.py
	mkdir -p $(PLIB)
	cp $^ $@

$(PLIB)/plugin_delay.py: ../../pylib/home_control/plugin_delay.py
	cp $^ $@

$(PLIB)/plugin_test.py: ../../pylib/home_control/plugin_test.py
	cp $^ $@

$(PLIB)/plugin_tplink.py: ../../pylib/home_control/plugin_tplink.py
	cp $^ $@

$(PLIB)/plugin_web.py: ../../pylib/home_control/plugin_web.py
	cp $^ $@

$(PLIB)/kcore/varz.py: ../../pylib/kcore/varz.py
	mkdir -p $(PLIB)/kcore
	cp $^ $@


# ---------- pass-throughs

include ../../common/Makefile-docker
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
