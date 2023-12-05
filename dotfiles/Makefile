
SHELL := bash
include ../etc/Makefile-colors

COMP = ../etc/comp.py

# ----------

HOME_DIR := $$HOME
HOME_FILES := .bashrc .ees.el .emacs .gitconfig .gitignore .profile .screenrc .screenrc-k1 .screenrc-ke
HOME_TARGETS := $(addprefix $(HOME_DIR)/, $(HOME_FILES))

BIN_DIR := $$HOME/bin
BIN_FILES := blib
BIN_TARGETS := $(addprefix $(BIN_DIR)/, $(BIN_FILES))

# ---------- custom logic

all:
	@echo "nothing to be done for :all"

clean:
	@echo "nothing to be done for :clean"

comp:
	@$(COMP) -b $(HOME_DIR) $(HOME_FILES)
	@$(COMP) -b $(BIN_DIR) $(BIN_FILES)

install:
	@printf "\n\n${RED}many of these scripts contain values specific to the original author.\n${YELLOW}They are really intended more as inspiration for your own dotfiles, rather than plug-in replacements.\n${CYAN}do you really want to overwrite your home-directory dotfiles...? ${RESET}\n\n"
	@read -p "ARE YOU SURE? " ans; if [[ "$$ans" == "y" ]]; then $(MAKE) dots; else echo "aborted"; fi

test:
	@echo "no tests currently available for dotfiles"

uninstall:
	@echo "removing dotfiles without replacements is dangerous; sorry; please prune things manually."

update: all test install


# ---------- custom target: install without verification

dots:	$(HOME_TARGETS) $(BIN_TARGETS)

$(HOME_TARGETS): $(HOME_DIR)/% : %
	cp -buv $^ $@

$(BIN_TARGETS): $(BIN_DIR)/% : %
	cp -buv $^ $@
