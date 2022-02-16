
# Handy Makefile reference: https://makefiletutorial.com/

TOP_TARGETS = all clean comp install test uninstall update

SUBDIRS ?= $(shell ls */Makefile | cut -d/ -f1)

$(TOP_TARGETS): $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

# This is a top-level dir only target (and the only one)
push: FORCE
	git commit -v -a
	git remote | xargs -L1 -I@ echo git pull @ ${GIT_BRANCH}
	git remote | xargs -L1 git push

FORCE:
