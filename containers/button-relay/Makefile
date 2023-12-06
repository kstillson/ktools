
H_DIR := files/home/relay
H_FILES := button_relay
H_TARGETS := $(addprefix $(H_DIR)/, $(H_FILES))

DIRS := $(H_DIR)

# ---------- local custom logic

all: copy docker-all

clean:
	rm -f $(H_TARGETS)

copy: $(DIRS) $(H_TARGETS)

$(DIRS):
	mkdir -p $@

$(H_TARGETS): $(H_DIR)/% : ../../tools-etc/%.py
	cp $^ $@


# ---------- pass-throughs

include ../../etc/Makefile-docker

comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
