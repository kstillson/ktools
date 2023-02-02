
# Supported meta-targets:  all, clean, test, install, update

PY_TARGETS := iptables_log_sum
SH_TARGETS := q
INSTALL_DIR := /root/bin
include ../etc/Makefile-common

# ---------- custom logic

clean:
	@echo "about to sudo for tools-for-root:clean -- these had to be installed by root, so can only be removed by root."
	sudo $(MAKE) common_clean

comp:
	@echo "about to sudo for tools-for-root:install -- these had to be installed by root, and generally permissions now require root to compare them."
	sudo $(MAKE) common_comp

install:
	@echo "about to sudo for tools-for-root:install -- these tools can only be used by root, so it is assumed you want to install them where root can use them."
	sudo $(MAKE) common_install

uninstall:
	@echo "about to sudo for container-infrastructure:uninstall -- these were installed for root by sudo, and so must be uninstalled that way."
	sudo $(MAKE) common_uninstall

update:
	@echo "about to sudo for tools-for-root:update -- these tools can only be used by root, so it is assumed you want to install them where root can use them."
	sudo $(MAKE) common_update

# ---------- testing

# uses 'script' to avoid stripping the color (as output redirection would).
$(TEST_LOG): $(wildcard *.py) $(wildcard *.sh) $(STAGING_DIR)
	script -eq -c "pytest-3 tests/test_*.py" $(TEST_LOG)
	script -aeq -c "./tests/test_q.sh" $(TEST_LOG)

# ---------- pass-throughs

all: common_all

test: common_test

