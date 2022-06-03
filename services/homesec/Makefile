
TEST_LOG ?= test.log

# ----------

# TODO: not obvious what a good install target dir would be.
# /usr/local/keymaster..?  probably should revisit this rather than silently
# doing nothing...


all:

comp: 

clean: 
	rm -rf $(TEST_LOG) __pycache__ */__pycache__ .pytest_cache

install: 

test: $(TEST_LOG)

uninstall: 

update: all test install

# ----- :test

$(TEST_LOG): $(wildcard *.py tests/*.py)
	script -e -c "pytest-3 tests" $(TEST_LOG)

