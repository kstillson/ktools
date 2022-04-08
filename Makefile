
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

# ---------- special additions to common targets

clean:
	$(MAKE) --no-print-directory -C docker-containers clean
	rm -rf home-control/__pycache__ common/prep-stamp

# ---------- everything

e:	everything

everything: prep
	$(MAKE) update   # all -> test -> install
	$(MAKE) --no-print-directory -C docker-containers/kcore-baseline update
	$(MAKE) --no-print-directory -C docker-containers update


# ---------- prep

prep:	common/prep-stamp

common/prep-stamp:	docker-containers/kcore-baseline/private.d/cert-settings
	mkdir -p services/keymaster/private.d
	cp -n services/keymaster/tests/km-test.data.gpg services/keymaster/private.d/km.data.gpg
	pgrep docker || echo "WARNING- docker daemon not detected.  docker-containers/** can't build or run without it.  You probably want to do something like:  sudo apt-get install docker.io"
	touch common/prep-stamp

docker-containers/kcore-baseline/private.d/cert-settings:
	mkdir -p docker-containers/kcore-baseline/private.d
	cp -n docker-containers/kcore-baseline/cert-settings.template docker-containers/kcore-baseline/private.d/cert-settings
	editor docker-containers/kcore-baseline/private.d/cert-settings


# ---------- push

# TODO: is this a good idea?
#push: FORCE
#	git commit -v -a
#	git remote | xargs -L1 -I@ echo git pull @ ${GIT_BRANCH}
#	git remote | xargs -L1 git push

FORCE:
