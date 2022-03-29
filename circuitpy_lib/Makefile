
PYTHON_TARGETS := $(wildcard *.py)
SHELL := /bin/bash
TEST_LOG := test.log

# ---------- standard targets

clean:
	rm -rf $(TEST_LOG)

# ---------- do-nothing standard targets

all:

clean:

comp:

install:

uninstall:

update:


# ---------- testing

test: $(TEST_LOG)

$(TEST_LOG): $(wildcard *.py) $(wildcard tests/*.py)
	script -eq -c "pytest-3 tests/test_*.py" $(TEST_LOG)


# ---------- specialized install target

install-hw:
	export D="/media/$(shell whoami)/CIRCUITPY/lib"; \
	  mkdir -p $$D/circuitpy_lib ; \
	  install $(PYTHON_TARGETS) $$D/circuitpy_lib ; \
	  install ../pylib/kcore/*.py $$D ; \
	  rm $$D/webserver.py

