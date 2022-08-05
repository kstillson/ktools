
PLIB := files/usr/lib/python3.9/site-packages
COPIED_FILES := files/usr/local/bin/kmc files/usr/local/bin/keymaster.crt \
    $(PLIB)/kcore

# ---------- local custom logic

# WARNING- all docker containers (except kcore-baseline) depend on
# kcore-baseline being built AND INSTALLED (i.e. marked :live) before the
# other containers can be BUILT.
#
# For this reason, kcore-baseline ":all" runs docker-update, which will BUILD,
# test *AND INSTALL* the baseline image.

all: copy baseline-stamp

baseline-stamp:
	@echo "about to sudo for docker container d-build command.  Containers can only be built by root."
	sudo -E /root/bin/d-build -t    # -E to preserve d-build environment vars
	sudo -E /root/bin/d-build -s    # -E to preserve d-build environment vars
	touch baseline-stamp


# for check_kcore_installed
include ../../etc/Makefile-common

# ---------- local customizations

clean:
	rm -rf $(COPIED_FILES) *-stamp

test:
	sudo $(MAKE) check_kcore_installed
	sudo $(MAKE) docker-test


# ---------- local additions

copy: $(PLIB) $(COPIED_FILES)

files/usr/local/bin/kmc: ../../pylib/tools/kmc.py
	mkdir --mode=755 --parents files/usr/local/bin
	cp $^ $@
	chmod 755 $@

files/usr/local/bin/keymaster.crt: ../../private.d/keymaster.crt
	mkdir --mode=755 --parents files/usr/local/bin
	cp $^ $@
	chmod 644 $@

$(PLIB):
	mkdir -p $@

$(PLIB)/kcore: ../../pylib/kcore
	cp -rpuv $^ $(PLIB)
	chmod -R go+rX $@


# ---------- pass-throughs

include ../../etc/Makefile-docker

comp:  # n/a
clean: docker-clean
install: docker-install
uninstall: docker-uninstall
update: docker-update

