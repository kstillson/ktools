
ULB_DIR := files/usr/local/bin

TOOL_FILES := nag
TOOL_TARGETS := $(addprefix $(ULB_DIR)/, $(TOOL_FILES))

ETC_FILES := party-lights.py tplink.py
ETC_TARGETS := $(addprefix $(ULB_DIR)/, $(ETC_FILES))

# ---------- local custom logic

all: copy docker-all

clean:
	rm -rf $(TOOL_TARGETS) $(ETC_TARGETS)

copy: $(TOOL_TARGETS) $(ETC_TARGETS)

$(TOOL_TARGETS): $(ULB_DIR)/% : ../../pylib/tools/%.py
	cp $^ $@

$(ETC_TARGETS): $(ULB_DIR)/% : ../../tools-etc/%
	cp $^ $@


# ---------- pass-throughs

include ../../etc/Makefile-docker

comp:  # n/a
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
