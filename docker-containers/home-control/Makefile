
include ../../common/Makefile-docker

# ---------- local additions (remove files copied over by ./Build)

clean:
	rm -rf files/home/hc/home_control_service.py files/home/hc/root.html files/usr/lib/python3.9/site-packages files/home/hc/hcdata_devices.py files/home/hc/hcdata_scenes.py files/home/hc/hcdata_test_device.py


# ---------- pass-throughs

all: docker-all
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
