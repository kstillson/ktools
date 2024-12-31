
include ../../etc/Makefile-common
SHELL := /bin/bash


# ---------- custom targets

clean: common_clear

$(TEST_LOG): $(wildcard *.py tests/*.py)
	pytest-3 test*.py > $@


# ---------- pass-throughs

test: common_test


# ---------- no-ops

all:
	@echo nothing to be done for :all

comp:
	@echo nothing to be done for :comp

install:
	@echo nothing to be done for :install

update:
	@echo nothing to be done for :update

uninstall:
	@echo nothing to be done for :uninstall
