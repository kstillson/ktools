
# Supported meta-targets:  all, clean, test, install, update

# "update" runs a all+test+install sequence, then a git sync sequences:
# commit local changes, pull from all remotes, then push to all remotes.

TARGETS = ratelimiter run_para

# Values assigned with "?=" can be overriden from the environment.
STAGING_DIR ?= staging
TEST_LOG ?= $(STAGING_DIR)/test.log
INSTALL_DIR ?= /root/bin
GIT_BRANCH ?= master

STAGING_TARGETS := $(patsubst %,$(STAGING_DIR)/%,$(TARGETS))
INSTALL_TARGETS := $(patsubst %,$(INSTALL_DIR)/%,$(TARGETS))

# ----------

all: $(STAGING_TARGETS)

# Pattern to create versions in the staging dir without the .py extension.
$(STAGING_TARGETS): $(STAGING_DIR)/%: %.py
	mkdir -p $(STAGING_DIR)
	install $^ $@

$(STAGING_DIR):
	mkdir -p $(STAGING_DIR)

clean:
	rm -rf $(STAGING_DIR) __pycache__ .pytest_cache

# NB: tests the .py files in the current dir, not the files in STAGING_DIR.
# Doesn't depend on "all", and can be run independently (unusual for a Makefile).
# uses 'script' to avoid stripping the color (as output redirection would).
test: $(TEST_LOG)
$(TEST_LOG): $(wildcard *.py) $(STAGING_DIR)
	script -c "pytest-3 test_*.py" $(TEST_LOG)

install: $(INSTALL_TARGETS)
$(INSTALL_TARGETS): $(STAGING_TARGETS)
	install $^ ${INSTALL_DIR}

update: all test install
	git commit -v -a
	git remote | xargs -L1 -I@ echo git pull @ ${GIT_BRANCH}
	git remote | xargs -L1 git push

