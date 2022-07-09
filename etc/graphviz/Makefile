
DOTS := $(wildcard *.dot)
TARGETS := $(patsubst %.dot,%.png,$(DOTS))

all: $(TARGETS)

$(TARGETS): %.png: %.dot
	dot -Tpng $^ > $@
