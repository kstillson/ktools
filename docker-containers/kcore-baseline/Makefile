
# ---------- local custom logic

# WARNING- all docker containers (except kcore-baseline) depend on
# kcore-baseline being built AND INSTALLED (i.e. marked :live) before the
# other containers can be BUILT.
#
# For this reason, kcore-baseline ":all" runs docker-update, which will BUILD,
# test *AND INSTALL* the baseline image.

all: copy baseline-stamp

baseline-stamp: $(wildcard Buil* Dockerfile settings.yaml files/* files/*/* files/*/*/*)
	d-build -t
	d-build -s
	touch baseline-stamp


# for check_kcore_installed
include ../../etc/Makefile-common

FULB := files/usr/local/bin
COPIED_FILES := $(FULB)/kmc $(FULB)/keymaster.crt $(KCORE_DIR)


# ---------- local customizations

clean:
	rm -rf $(COPIED_FILES) *-stamp

test:
	$(MAKE) check_kcore_installed
	$(MAKE) docker-test


# ---------- local additions

copy: $(COPIED_FILES)

files/usr/local/bin/kmc: ../../pylib/tools/kmc.py
	mkdir --mode=755 --parents files/usr/local/bin
	cp $^ $@
	chmod 755 $@

files/usr/local/bin/keymaster.crt: ../../private.d/keymaster.crt
	mkdir --mode=755 --parents files/usr/local/bin
	cp $^ $@
	chmod 644 $@

$(KCORE_DIR): ../../pylib/kcore
	cp -rpuv $^ $(PLIB)
	chmod -R go+rX $@


# ---------- pass-throughs

include ../../etc/Makefile-docker

comp:  # n/a
clean: docker-clean
install: docker-install
uninstall: docker-uninstall
update: docker-update

