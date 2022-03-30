
TOP_TARGETS = all clean comp install test uninstall update

# specify SUBDIRS as an environment variable for partial work.
SUBDIRS ?= $(shell ls */Makefile | cut -d/ -f1)

$(TOP_TARGETS): $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

FORCE:

