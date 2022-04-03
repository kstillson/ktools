
# Handy Makefile reference: https://makefiletutorial.com/

TOP_TARGETS = all clean comp install test uninstall update

# Note: docker-containers is excluded from the list of subdirs because
# (a) building docker images requires root privs, and folks would rightly be
#     concerned about a "make all" asking for sudo rights
# (b) building docker images requires the docker-infrastructure/ targets
#     to be INSTALLED before docker-containers can be BUILT.
# (c) buidling and installing docker images needs to be carefully ordered,
#     as some depend on others, and the dependent ones cannot be BUILT
#     until the dependency is INSTALLED (i.e. tagged as :live).
#
# All of this is why the :everything target (shortcut :e) is provided;
# it will build, test, and install everything, all in the right order.


# specify SUBDIRS as an environment variable for partial work.
# remember that order matters.
SUBDIRS ?= pylib circuitpy_lib tools-for-root services docker-infrastructure

$(TOP_TARGETS): $(SUBDIRS)
$(SUBDIRS):
	$(MAKE) --no-print-directory -C $@ $(MAKECMDGOALS)

# Always run top-level rules, as subdirs might have their own phony targets.
.PHONY: $(TOPTARGETS) $(SUBDIRS)

# ---------- special additions

clean:
	$(MAKE) --no-print-directory -C docker-containers clean
	rm -rf home-control/__pycache__

# ---------- everything

e:	everything

everything:
	$(MAKE) update   # all -> test -> install
	$(MAKE) --no-print-directory -C docker-containers/kds-baseline update
	$(MAKE) --no-print-directory -C docker-containers update


# ---------- push

# TODO: is this a good idea?
#push: FORCE
#	git commit -v -a
#	git remote | xargs -L1 -I@ echo git pull @ ${GIT_BRANCH}
#	git remote | xargs -L1 git push

FORCE:
