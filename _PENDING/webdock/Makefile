
NAG_DIR := files/etc/nagios

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(NAG_DIR)

copy: $(NAG_DIR)

$(NAG_DIR):
	mkdir -p $@
	cp -r -puv ../nagdock/$(NAGDIR) $(NAG_DIR)


# ---------- pass-throughs

include ../../common/Makefile-docker
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
