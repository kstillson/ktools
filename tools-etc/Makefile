
SHELL := bash
include ../etc/Makefile-colors

COMP = ../etc/comp.py

# ---------- custom logic

all:
	@echo "nothing to be done for :all"

clean:
	@echo "nothing to be done for :clean"

comp:
	@if [[ "$$KTOOLS_KEN" == "jack" ]]; then $(MAKE) comp-jack; exit 0; else echo "target :comp not supported yet; sorry.  TODO(defer)"; fi

install:
	@if [[ "$$KTOOLS_KEN" == "jack" ]]; then $(MAKE) install-jack; exit 0; else echo "target :install not supported yet; sorry.  TODO(defer)"; fi

test:
	@echo "no tests currently available for tools-etc"

uninstall:
	@if [[ "$$KTOOLS_KEN" == "jack" ]]; then $(MAKE) uninstall-jack; exit 0; else echo "target :uninstall not supported yet; sorry.  TODO(defer)"; fi

update: all test install


# ---------- KTOOLS_KEN specific

KTE_DIR := /root/ktools/tools-etc
KTE_FILES := button_relay.py kds-button_relay.service
KTE_TARGETS := $(addprefix $(KTE_DIR)/, $(KTE_FILES))

RB_DIR := /root/bin
RB_FILES := m
RB_TARGETS := $(addprefix $(RB_DIR)/, $(RB_FILES))

ULB_DIR := /usr/local/bin
ULB_FILES := sunsetter.py
ULB_TARGETS := $(addprefix $(ULB_DIR)/, $(ULB_FILES))


# ----- install

install-jack: $(KTE_TARGETS) $(RB_TARGETS) $(ULB_TARGETS)
	@printf "\n$(YELLOW)install exceptions:$(RESET)\n\n"
	@echo "party-lights.py, tplink.py are pulled by ../docker-containers/webdock/Makefile"
	@echo "pb-push.sh is pulled by ../docker-containers/homesecdoc/Makefile"
	@echo "speak-cgi.py and speak.py need to be maually copied to pi1 for install."
	@echo ""

$(KTE_DIR)/button_relay.py: button_relay.py
	cp $^ $@

$(KTE_DIR)/kds-button_relay.service: button_relay.service
	cp $^ $@

$(RB_DIR)/m: m.py
	cp $^ $@

$(ULB_DIR)/sunsetter.py: sunsetter.py
	cp $^ $@


# ----- comp

comp-jack:
	@$(COMP) -b $(KTE_DIR) button_relay.py
	@$(COMP) -b $(KTE_DIR) -R 'kds-/' kds-button_relay.service
	@$(COMP) -b $(RB_DIR) -L '.py/' m.py
	@$(COMP) -b $(ULB_DIR) sunsetter.py

# ----- remove

uninstall-jack:
	rm -f $(KTE_TARGETS) $(RB_TARGETS) $(ULB_TARGETS)

