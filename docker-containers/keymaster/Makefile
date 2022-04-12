
KMH := files/home/km
PLIB := files/usr/lib/python3.9/site-packages
COPIED_FILES := $(KMH)/km.py $(KMH)/keymaster.pem $(KMH)/km.data.gpg $(KMH)/km-test.data.gpg \
    $(PLIB)/kcore/auth.py $(PLIB)/kcore/common.py $(PLIB)/kcore/common_base.py $(PLIB)/kcore/html.py \
    $(PLIB)/kcore/log_queue.py $(PLIB)/kcore/uncommon.py $(PLIB)/kcore/varz.py \
    $(PLIB)/kcore/webserver.py $(PLIB)/kcore/webserver_base.py 

# ---------- local additions (remove files copied over by ./Build)

all: docker-all

docker-all: $(COPIED_FILES)

clean:
	rm -f $(COPIED_FILES)

$(KMH)/km.py: ../../services/keymaster/km.py
	mkdir -p $(KMH)
	cp $^ $@

$(KMH)/keymaster.pem: ../../private.d/keymaster.pem
	cp $^ $@
	chmod 640 $@

$(KMH)/km.data.gpg: ../../private.d/km.data.gpg
	cp $^ $@

$(KMH)/km-test.data.gpg: ../../services/keymaster/tests/km-test.data.gpg
	cp $^ $@

$(PLIB)/kcore/auth.py: ../../pylib/kcore/auth.py
	mkdir -p $(PLIB)/kcore
	cp $^ $@
	chmod 644 $@

$(PLIB)/kcore/common.py: ../../pylib/kcore/common.py
	cp $^ $@
	chmod 644 $@

$(PLIB)/kcore/common_base.py: ../../pylib/kcore/common_base.py
	cp $^ $@
	chmod 644 $@

$(PLIB)/kcore/html.py: ../../pylib/kcore/html.py
	cp $^ $@
	chmod 644 $@

$(PLIB)/kcore/log_queue.py: ../../pylib/kcore/log_queue.py
	cp $^ $@
	chmod 644 $@

$(PLIB)/kcore/uncommon.py: ../../pylib/kcore/uncommon.py
	cp $^ $@
	chmod 644 $@

$(PLIB)/kcore/varz.py: ../../pylib/kcore/varz.py
	cp $^ $@
	chmod 644 $@

$(PLIB)/kcore/webserver.py: ../../pylib/kcore/webserver.py
	cp $^ $@
	chmod 644 $@

$(PLIB)/kcore/webserver_base.py: ../../pylib/kcore/webserver_base.py
	cp $^ $@
	chmod 644 $@

# -----

../../private.d/km.data.gpg: ../../services/keymaster/tests/km-test.data.gpg
	@echo "COULD NOT FIND $@, SO USING $^ AS A STARTING POINT"
	cp $^ $@


# ---------- pass-throughs

include ../../common/Makefile-docker
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
