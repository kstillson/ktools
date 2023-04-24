
GC_DIR := files/home/santa

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(GC_DIR)

copy: $(GC_DIR)

files/home/santa: ../../services/gift-coordinator/*
	mkdir -p $@
	cp -pr $^ $@


# ---------- pass-throughs

include ../../etc/Makefile-docker

all: docker-all
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
