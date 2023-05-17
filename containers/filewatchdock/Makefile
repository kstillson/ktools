
HW_DIR := files/home/watch
HW_FILES := filewatch filewatch_config
HW_TARGETS := $(addprefix $(HW_DIR)/, $(HW_FILES))
HW_TEST_FILES := test_filewatchdock.py filewatch_config_test
HW_TEST_TARGETS := $(addprefix $(HW_DIR)/, $(HW_TEST_FILES))

DIRS := $(HW_DIR)

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(HW_DIR)

copy: $(DIRS) $(HW_TARGETS) $(HW_TEST_TARGETS)

$(DIRS):
	mkdir -p $@

$(HW_TARGETS): $(HW_DIR)/% : ../../services/filewatch/%.py
	cp $^ $@

$(HW_TEST_TARGETS): $(HW_DIR)/% : ../../services/filewatch/tests/%
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
