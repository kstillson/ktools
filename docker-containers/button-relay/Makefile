
H_DIR := files/home/relay
H_FILES := button_relay
H_TARGETS := $(addprefix $(H_DIR)/, $(H_FILES))

DIRS := $(H_DIR)

# ---------- local custom logic

all: copy Dockerfile $(H_TARGETS)
	DOCKER_EXEC=podman DBUILD_PARAMS="--userns=host" $(MAKE) docker-all

clean:
	rm -rf $(H_DIR)

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
