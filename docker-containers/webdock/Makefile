
ULB_DIR := files/usr/local/bin

TOOL_FILES := nag
TOOL_TARGETS := $(addprefix $(ULB_DIR)/, $(TOOL_FILES))

ETC_FILES := party-lights
ETC_TARGETS := $(addprefix $(ULB_DIR)/, $(ETC_FILES))

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(TOOL_TARGETS) $(ETC_TARGETS)

copy: $(TOOL_TARGETS) $(ETC_TARGETS)

$(TOOL_TARGETS): $(ULB_DIR)/% : ../../pylib/tools/%.py
	cp $^ $@

$(ETC_TARGETS): $(ULB_DIR)/% : ../../pylib/etc/%.py
	cp $^ $@


# ---------- pass-throughs

include ../../common/Makefile-docker

comp:  # n/a
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
