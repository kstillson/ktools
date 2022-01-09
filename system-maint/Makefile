
# Supported meta-targets:  all, clean, test, install, update

# "update" runs a all+test+install sequence, then a git sync sequences:
# commit local changes, pull from all remotes, then push to all remotes.

TARGETS = q

# Values assigned with "?=" can be overriden from the environment.
STAGING_DIR ?= staging
TEST_LOG ?= $(STAGING_DIR)/test.log
INSTALL_DIR ?= /root/bin
GIT_BRANCH ?= master

STAGING_TARGETS := $(patsubst %,$(STAGING_DIR)/%,$(TARGETS))
INSTALL_TARGETS := $(patsubst %,$(INSTALL_DIR)/%,$(TARGETS))

# ----------

all: $(STAGING_TARGETS)

# Pattern to create versions in the staging dir without the .sh extension.
$(STAGING_TARGETS): $(STAGING_DIR)/%: %.sh
	mkdir -p $(STAGING_DIR)
	install $^ $@

$(STAGING_DIR):
	mkdir -p $(STAGING_DIR)

clean:
	rm -rf $(STAGING_DIR)

test:
	echo "not tests ready yet; default to pass"
	exit 0

install: $(INSTALL_TARGETS)
$(INSTALL_TARGETS): $(STAGING_TARGETS)
	install $^ ${INSTALL_DIR}

update: all test install
	git commit -v -a
	git remote | xargs -L1 -I@ echo git pull @ ${GIT_BRANCH}
	git remote | xargs -L1 git push

