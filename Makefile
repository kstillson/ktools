
# Handy Makefile reference: https://makefiletutorial.com/

TOP_TARGETS = all clean install test

SUBDIRS = $(shell ls */Makefile | cut -d/ -f1)

$(TOP_TARGETS): $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)
