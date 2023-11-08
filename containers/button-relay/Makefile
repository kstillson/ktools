
H_DIR := files/home/relay
H_FILES := button_relay
H_TARGETS := $(addprefix $(H_DIR)/, $(H_FILES))

DIRS := $(H_DIR)

# ---------- local custom logic

#all: copy Dockerfile $(H_TARGETS)
all: copy docker-all

clean:
	rm -rf $(H_DIR)

copy: $(DIRS) $(H_TARGETS)

$(DIRS):
	mkdir -p $@

$(H_TARGETS): $(H_DIR)/% : ../../tools-etc/%.py
	cp $^ $@

test:
	@echo "no tests yet"


# ---------- pass-throughs

include ../../etc/Makefile-docker

comp:  # n/a
clean: docker-clean
install: docker-install
uninstall: docker-uninstall
update: docker-update
