
INSTALLED_TOOLS := hc k_auth kmc nag pcrypt ratelimiter run_para
SHELL := /bin/bash
TEST_LOG ?= test.log

LOCAL_SITE_DIR ?= $(shell python3 -m site --user-site)
INSTALL_BASE := $(shell echo $${VIRTUAL_ENV:-$(LOCAL_SITE_DIR)})

CIRCUITPY_DIR ?= /media/$$USER/CIRCUITPY

COMP = ../etc/comp.py

# Must be kept up-to-date with version number from ./setup.cfg
WHEEL := dist/kcore_pylib-0.9-py3-none-any.whl

include ../etc/Makefile-colors

# ---------- standard targets

all:
	if [[ "$$BUILD_SIMPLE" == "1" ]]; then $(MAKE) all-simple; else $(MAKE) all-wheel; fi

clean:
	rm -rf $(TEST_LOG) */__pycache__ */*/__pycache__ .pytest_cache */.pytest_cache */*/.pytest_cache dist *.egg-info tools/keymaster.crt
	@printf "\n NOT cleaning the $(YELLOW)venv directory$(RESET).  use make target 'vclean' or remove manually if needed.\n\n"

comp:
	@$(COMP) -b "$(INSTALL_BASE)" -L 'tools/ktools' circuitpy_sim/*.py home_control/*.py kcore/*.py tools/*.py

install:
	if [[ "$$BUILD_SIMPLE" == "1" ]]; then $(MAKE) install-simple; else $(MAKE) install-wheel; fi

test: $(TEST_LOG)

uninstall:
	if [[ "$$BUILD_SIMPLE" == "1" ]]; then $(MAKE) uninstall-simple; else $(MAKE) uninstall-wheel; fi

update:
	$(MAKE) all test install


# ---------- custom sub-rules for the standard targets

# ----- :all

all-simple: tools/keymaster.crt

all-wheel: tools/keymaster.crt $(WHEEL)

tools/keymaster.crt: ../private.d/keymaster.crt
	cp -bpuv $^ $@

$(WHEEL): venv/bin/activate $(wildcard */*.py)
	source venv/bin/activate && python3 -m build

# ----- :install

install-wheel: $(WHEEL)
	@if [[ -v VIRTUAL_ENV ]]; then printf "\n $(shell tput setaf 3) NOTICE- $(shell tput sgr0) installing into virtual environtment ${VIRTUAL_ENV}.  If that's not what you want, type command 'deactivate' and run the install again.\n\n"; fi
	@if [[ "$UID" == "0" ]]; then printf "\n $(shell tput setaf 3) NOTICE- $(shell tput sgr0) installing into root's .local directory.  Use target 'install-system' to install into /usr/local for all users."; fi
	pip3 install -U $(shell if [[ ! -v VIRTUAL_ENV ]]; then echo "--user "; fi) $(WHEEL)

# Skip the whole packaging and wheel generation; just copy updated source files
# directly info to ~/.local.  This has some hard-coded path assumptions, and
# won't automatically pick up new subdirs, so it might not work at all for you.
# But when making lots of changes, this is quicker (when it works).
install-simple: tools/keymaster.crt
	rm -rf */__pycache__ */.pytest_cache
	mkdir -p $(LOCAL_SITE_DIR) ~/.local/bin
	# circuitpy_sim
	rm -rf $(LOCAL_SITE_DIR)/circuitpy_sim
	mkdir -p $(LOCAL_SITE_DIR)/circuitpy_sim
	cp -r -puv circuitpy_sim/* $(LOCAL_SITE_DIR)/circuitpy_sim
	# home_control
	rm -rf $(LOCAL_SITE_DIR)/home_control
	mkdir -p $(LOCAL_SITE_DIR)/home_control
	cp -puv home_control/* $(LOCAL_SITE_DIR)/home_control
	cp -puv home_control/hc.py ~/.local/bin/hc
	# kcore
	rm -rf $(LOCAL_SITE_DIR)/kcore
	mkdir -p $(LOCAL_SITE_DIR)/kcore
	cp -puv kcore/* $(LOCAL_SITE_DIR)/kcore
	cp -puv kcore/auth.py ~/.local/bin/k_auth
	# ktools
	rm -rf $(LOCAL_SITE_DIR)/ktools
	mkdir -p $(LOCAL_SITE_DIR)/ktools
	cp -puv tools/* $(LOCAL_SITE_DIR)/ktools
	cp -puv tools/keymaster.crt ~/.local/bin/keymaster.crt
	cp -puv tools/nag.py ~/.local/bin/nag
	cp -puv tools/pb-push.sh ~/.local/bin/pb-push
	cp -puv tools/pcrypt.py ~/.local/bin/pcrypt
	cp -puv tools/ratelimiter.py ~/.local/bin/ratelimiter
	cp -puv tools/run_para.py ~/.local/bin/run_para
	#
	$(MAKE) link


# ----- :test

$(TEST_LOG): $(wildcard */*.py */*/*.py)
	script -e -c "pytest-3 tests" $(TEST_LOG)

# ----- :uninstall

uninstall-wheel:
	@if [[ -v VIRTUAL_ENV ]]; then echo "uninstalling from virtual environtment ${VIRTUAL_ENV}."; fi
	pip3 uninstall kcore_pylib

uninstall-simple:
	$(MAKE) unlink
	rm -rf $(LOCAL_SITE_DIR)/kcore
	rm -rf $(LOCAL_SITE_DIR)/ktools
	rm -rf $(LOCAL_SITE_DIR)/home_control


# ---------- specialized installation targets

install-system: $(WHEEL)
	@if [[ -v VIRTUAL_ENV ]]; then echo "ERROR- install-system not compatible with virtual environment.  Try command 'deactivate' and run again."; exit 1; fi
	umask 022; pip3 install --system --upgrade $(WHEEL)

# Create symlinks from wherever we installed our executable scripts to the user's ~/bin dir.
link:
	sdir=$${VIRTUAL_ENV:-~/.local} && for x in $(INSTALLED_TOOLS); do ln -fs $$sdir/bin/$$x $$HOME/bin/$$x; done

unlink:
	for x in $(INSTALLED_TOOLS); do rm -f ~/bin/$$x; done

install-circuitpy:
	@if [[ ! -d $(CIRCUITPY_DIR)/lib ]]; then echo "ERROR- cannot find $(CIRCUITPY_DIR)/lib"; exit 1; fi
	mkdir -p $(CIRCUITPY_DIR)/lib/kcore
	FILES="$(shell ls -1 kcore/*.py | egrep -v '__init__|docker_lib|uncommon|webserver\.py')" && cp -bpuv $$FILES $(CIRCUITPY_DIR)/lib/kcore
	cp -bpuv ../private.d/wifi_secrets.py $(CIRCUITPY_DIR)
	cp -bpuv tests/kcore/server.py $(CIRCUITPY_DIR)/code.py
	@echo "you should now be ready to:"
	@echo " TESTHOST=testcircpy pytest-3 tests/kcore/test_webserver_circpy.py "


# ---------- virtual environment support

venv: venv/bin/activate

venv/bin/activate:
	python3 -m venv venv
	source venv/bin/activate && python3 -m pip install -U build --no-warn-script-location
	@echo "venv ready; to enter, use command:    source venv/bin/activate"

vclean:
	$(MAKE) clean |& fgrep -v 'not cleaning'
	rm -rf venv

