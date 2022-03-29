
INSTALLED_SCRIPTS := k_auth kmc ratelimiter run_para
SHELL := /bin/bash
TEST_LOG ?= test.log

LAST_WHEEL = $(shell ls -t1 dist/*.whl | tail -1)

# ---------- standard targets

all: dist/build-touch

clean:
	rm -rf $(TEST_LOG) */__pycache__ */*/__pycache__ .pytest_cache dist *.egg-info
	@echo "note: not cleaning the venv directory.  use make target 'vclean' or remove manually if needed."

comp:
	@sdir=$${VIRTUAL_ENV:-~/.local} && for t in kcore/*.py; do diff -sq $$t $$sdir/lib/python*/site-packages/$$t | sed -e "/identical/s@.*@ok: $$t@"; done
	@sdir=$${VIRTUAL_ENV:-~/.local} && for t in tools/*.py; do diff -sq $$t $$sdir/lib/python*/site-packages/$${t/tools/ktools} | sed -e "/identical/s@.*@ok: $$t@"; done

install:
	@if [[ -v VIRTUAL_ENV ]]; then echo "NOTICE- installing into virtual environtment ${VIRTUAL_ENV}.  If that's not what you want, type command 'deactivate' and run the install again."; fi
	pip3 install $(LAST_WHEEL)

test: $(TEST_LOG)

uninstall:
	@if [[ -v VIRTUAL_ENV ]]; then echo "uninstalling from virtual environtment ${VIRTUAL_ENV}."; fi
	pip3 uninstall kcore_pylib

update:  # TODO


# ---------- custom sub-rules for the standard targets

# :all 
dist/build-touch: $(wildcard */.py) venv/bin/activate
	source venv/bin/activate && python3 -m build
	touch dist/build-touch

# :test
$(TEST_LOG): $(wildcard */*.py */*/*.py)
	script -c "pytest-3 tests" $(TEST_LOG)


# ---------- custom targets

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

