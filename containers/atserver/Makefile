
HW_DIR := files/home/atsvc
HW_FILES := atserver.py root.html
HW_TARGETS := $(addprefix $(HW_DIR)/, $(HW_FILES))

DIRS := $(HW_DIR)

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(HW_DIR)

copy: $(DIRS) $(HW_TARGETS)

$(DIRS):
	mkdir -p $@

$(HW_TARGETS): $(HW_DIR)/% : ../../services/atserver/%
	cp $^ $@


# ---------- pass-throughs

include ../../etc/Makefile-docker

all: docker-all
comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
