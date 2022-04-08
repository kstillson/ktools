
include ../../common/Makefile-docker

# ---------- local additions (remove files copied over by ./Build)

clean:
	rm -f files/home/km/km.py files/home/km/km-test.data.gpg files/home/km/km.data.gpg


# ---------- pass-throughs

all: docker-all
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
