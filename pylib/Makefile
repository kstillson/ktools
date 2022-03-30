
INSTALLED_SCRIPTS := k_auth kmc ratelimiter run_para
SHELL := /bin/bash
TEST_LOG ?= test.log

LAST_WHEEL = $(shell ls -t1 dist/*.whl | tail -1)

# ---------- standard targets

## TEMP: disable wheel in favor of simple install.
## all: dist/build-touch
all:

clean:
	rm -rf $(TEST_LOG) */__pycache__ */*/__pycache__ .pytest_cache dist *.egg-info
	@echo "note: not cleaning the venv directory.  use make target 'vclean' or remove manually if needed."

comp:
	@sdir=$${VIRTUAL_ENV:-~/.local} && for t in kcore/*.py; do diff -sq $$t $$sdir/lib/python*/site-packages/$$t | sed -e "/identical/s@.*@ok: $$t@"; done
	@sdir=$${VIRTUAL_ENV:-~/.local} && for t in tools/*.py; do diff -sq $$t $$sdir/lib/python*/site-packages/$${t/tools/ktools} | sed -e "/identical/s@.*@ok: $$t@"; done

## TEMP: disable wheel in favor of simple install.
## install: install_via_wheel
install: install-simple

install_via_wheel:
	@if [[ -v VIRTUAL_ENV ]]; then echo "NOTICE- installing into virtual environtment ${VIRTUAL_ENV}.  If that's not what you want, type command 'deactivate' and run the install again."; fi
	@if [[ "$UID" == "0" ]]; then echo "NOTICE- installing into root's .local directory.  Use target 'install-system' to install into /usr/local for all users."; fi
	pip3 install -U --user $(LAST_WHEEL)

test: $(TEST_LOG)

uninstall:
	@if [[ -v VIRTUAL_ENV ]]; then echo "uninstalling from virtual environtment ${VIRTUAL_ENV}."; fi
	pip3 uninstall kcore_pylib

update:  # TODO


# ---------- custom sub-rules for the standard targets

# :all 
dist/build-touch: $(wildcard */*.py) venv/bin/activate
	source venv/bin/activate && python3 -m build
	touch dist/build-touch

# :test
$(TEST_LOG): $(wildcard */*.py */*/*.py)
	script -c "pytest-3 tests" $(TEST_LOG)


# ---------- custom targets

# Skip the whole packaging and wheel generation; just copy updated source files
# directly info to ~/.local.  This has some hard-coded path assumptions, and
# won't automatically pick up new subdirs, so it might not work at all for you.
# But when making lots of changes, this is quicker (when it works).
install-simple:
	/usr/bin/rm -rf */__pycache__ */.pytest_cache
	/usr/bin/rm -rf ~/.local/lib/python3.8/site-packages/kcore
	/usr/bin/mkdir -p ~/.local/lib/python3.8/site-packages/kcore
	/usr/bin/cp -puv kcore/* ~/.local/lib/python3.8/site-packages/kcore
	/usr/bin/rm -rf ~/.local/lib/python3.8/site-packages/ktools
	/usr/bin/mkdir -p ~/.local/lib/python3.8/site-packages/ktools
	/usr/bin/cp -puv tools/* ~/.local/lib/python3.8/site-packages/ktools


install-system:
	@if [[ -v VIRTUAL_ENV ]]; then echo "ERROR- install-system not compatible with virtual environment.  Try command 'deactivate' and run again."; exit 1; fi
	@if [[ "$UID" != "0"_ENV ]]; then echo "ERROR- gotta be root for this.  Use regular 'install' target for individual user installs."; exit 1; fi
	pip3 install -U $(LAST_WHEEL)


# Create symlinks from wherever we installed our executable scripts to the user's ~/bin dir.
link:
	sdir=$${VIRTUAL_ENV:-~/.local} && for x in $(INSTALLED_SCRIPTS); do ln -s $$sdir/bin/$$x ~/bin/$$x; done

unlink:
	for x in $(INSTALLED_SCRIPTS); do rm ~/bin/$$x; done


# ---------- virtual environment support

venv: venv/bin/activate

venv/bin/activate:
	python3 -m venv venv
	source venv/bin/activate && python3 -m pip install -U build --no-warn-script-location
	@echo "venv ready; to enter, use command:    source venv/bin/activate"

vclean:	clean
	rm -rf venv

