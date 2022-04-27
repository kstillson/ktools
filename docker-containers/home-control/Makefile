
HCH := files/home/hc
PLIB := files/usr/lib/python3.9/site-packages
COPIED_FILES := $(HCH)/home_control_service.py $(HCH)/root.html \
   $(HCH)/hcdata_devices.py $(HCH)/hcdata_scenes.py $(HCH)/hcdata_test_device.py  \
   $(PLIB)/home_control/hc.py $(PLIB)/home_control/plugin_delay.py $(PLIB)/home_control/plugin_test.py \
   $(PLIB)/home_control/plugin_tplink.py $(PLIB)/home_control/plugin_web.py \
   $(PLIB)/kcore/common.py $(PLIB)/kcore/html.py $(PLIB)/kcore/log_queue.py \
   $(PLIB)/kcore/webserver_base.py $(PLIB)/kcore/webserver.py $(PLIB)/kcore/varz.py 


# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(COPIED_FILES)

copy: $(COPIED_FILES) 

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

$(PLIB)/home_control/hc.py: ../../pylib/home_control/hc.py
	mkdir -p $(PLIB)/home_control
	cp $^ $@

$(PLIB)/home_control/plugin_delay.py: ../../pylib/home_control/plugin_delay.py
	cp $^ $@

$(PLIB)/home_control/plugin_test.py: ../../pylib/home_control/plugin_test.py
	cp $^ $@

$(PLIB)/home_control/plugin_tplink.py: ../../pylib/home_control/plugin_tplink.py
	cp $^ $@

$(PLIB)/home_control/plugin_web.py: ../../pylib/home_control/plugin_web.py
	cp $^ $@

$(PLIB)/kcore/common.py: ../../pylib/kcore/common.py
	mkdir -p $(PLIB)/kcore
	cp $^ $@

$(PLIB)/kcore/html.py: ../../pylib/kcore/html.py
	cp $^ $@

$(PLIB)/kcore/log_queue.py: ../../pylib/kcore/log_queue.py
	cp $^ $@

$(PLIB)/kcore/webserver_base.py: ../../pylib/kcore/webserver_base.py
	cp $^ $@

$(PLIB)/kcore/webserver.py: ../../pylib/kcore/webserver.py
	cp $^ $@

$(PLIB)/kcore/varz.py: ../../pylib/kcore/varz.py
	cp $^ $@


# ---------- pass-throughs

include ../../common/Makefile-docker
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
