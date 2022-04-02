TOP_TARGETS = all clean comp install test uninstall update

# WARNING- all docker containers except kcore_baseline depend on kcore_baseline
# being built AND INSTALLED (i.e. marked :live) before the other containers
# can be BUILT.
#
# For this reason, kcore_baseline is EXCLUDED from the SUBDIRS variable below,
# and must be built and installed BEFORE any other targets are built.
#
SUBDIRS ?= $(shell ls */Makefile | cut -d/ -f1 | fgrep -v kcore-baseline)

$(TOP_TARGETS): $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

# ---------- special additions

clean:
	$(MAKE) --no-print-directory -C kcore-baseline clean

