
# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := iptables_log_sum
SH_TARGETS := q
INSTALL_DIR := /root/bin
include ../common/Makefile-unstaged

# ---------- custom logic

clean:
	sudo $(MAKE) common_clean

install:
	sudo $(MAKE) common_install

uninstall:
	sudo $(MAKE) common_uninstall

update:
	sudo $(MAKE) common_update

# ---------- testing

# uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard *.sh) $(STAGING_DIR)
	script -eq -c "pytest-3 tests/test_*.py" $(TEST_LOG)
	script -aeq -c "./tests/test_q.sh" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

comp: common_comp

test: common_test

