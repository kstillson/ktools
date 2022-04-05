
TEST_LOG ?= test.log

# ----------

all: 

comp: 

clean: 
	rm -rf $(TEST_LOG) __pycache__ */__pycache__ .pytest_cache

install: 

test: $(TEST_LOG)

uninstall: 

update: all test install

# ----- :test

$(TEST_LOG): $(wildcard */*.py */*/*.py)
	script -e -c "pytest-3 tests" $(TEST_LOG)

