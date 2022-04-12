
PLIB := files/usr/lib/python3.9/site-packages
COPIED_FILES := files/usr/local/bin/kmc files/usr/local/bin/keymanager.crt \
    $(PLIB)/kcore/auth.py

# ---------- local custom logic

# WARNING- all docker containers (except kcore-baseline) depend on
# kcore-baseline being built AND INSTALLED (i.e. marked :live) before the
# other containers can be BUILT.
#
# For this reason, kcore-baseline ":all" runs docker-update, which will BUILD,
# test *AND INSTALL* the baseline image.

all: $(COPIED_FILES) docker-update


# the generic docker-build has a dep on the kcore install-stamp, but obviously
# we need to break that dependency or it'll cause a cycle.  So just put in a
# rule here that says there's no dep for install-stamp here.  Seems to work.
../kcore-baseline/install-stamp:


# ---------- local additions

clean:
	rm -rf $(COPIED_FILES)

files/usr/local/bin/kmc: ../../pylib/tools/kmc.py
	mkdir -p files/usr/local/bin
	cp $^ $@

files/usr/local/bin/keymanager.crt: ../../private.d/keymaster.crt
	mkdir -p files/usr/local/bin
	cp $^ $@

$(PLIB)/kcore/auth.py: ../../pylib/kcore/auth.py
	mkdir -m 755 -p $(PLIB)/kcore
	cp $^ $@
	chmod 755 $@


# ---------- pass-throughs

include ../../common/Makefile-docker

comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update

