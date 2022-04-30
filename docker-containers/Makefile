TOP_TARGETS = all clean install test update

# WARNING- all docker containers (except kcore-baseline) depend on
# kcore-baseline being built AND INSTALLED (i.e. marked :live) before the
# other containers can be BUILT.
#
# For this reason, kcore-baseline is listed first here, and the :all target
# for kcore-baseline will BUILD, test AND INSTALL.
#
SUBDIRS ?= kcore-baseline $(shell ls */Makefile | cut -d/ -f1 | fgrep -v kcore-baseline)

$(TOP_TARGETS): $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

# ---------- special additions

clean:
	$(MAKE) --no-print-directory -C kcore-baseline clean

