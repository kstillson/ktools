
# TODO: Ken specific registry name and ports; generalize...?
CERTNAME := regdock
PORT1 := 5443
PORT2 := 5444

# note: make doesn't work well with filenames that contain ":"'s.
# temporarily use "__".  This gets fixed up in files/prep-local.
CD_FILE := regdock.crt
CDIR_BASE := files/etc/containers/certs.d
CD_SRC_DIR := ../registry/files/etc/private.d
CDIR1 := $(CDIR_BASE)/$(CERTNAME)__$(PORT1)
CDIR1_TARGET := $(addprefix $(CDIR1)/, $(CD_FILE))
CDIR2 := $(CDIR_BASE)/$(CERTNAME)__$(PORT2)
CDIR2_TARGET := $(addprefix $(CDIR2)/, $(CD_FILE))

ULB_DIR := files/usr/local/bin
ULB_FILES := run_para
ULB_TARGETS := $(addprefix $(ULB_DIR)/, $(ULB_FILES))

DIRS := $(CDIR1) $(CDIR2) $(ULB_DIR)

SSH_KEY = files/root/.ssh/private.d/id_rsa

# ---------- local custom logic

all: copy $(SSH_KEY) docker-all

clean:
	rm -rf files/etc/containers

# ---- copy

copy: $(DIRS) $(CDIR1_TARGET) $(CDIR2_TARGET) $(ULB_TARGETS)

$(DIRS):
	mkdir -p $@

$(CDIR1_TARGET): $(CD_SRC_DIR)/$(CD_FILE)
	cp $^ $@

$(CDIR2_TARGET): $(CD_SRC_DIR)/$(CD_FILE)
	cp $^ $@

$(ULB_TARGETS): $(ULB_DIR)/% : ../../pylib/tools/%.py
	cp $^ $@

# ---- ssh key

$(SSH_KEY):
	ssh-keygen -C root@builder -N '' -f $@

# ---------- pass-throughs

include ../../etc/Makefile-docker

comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
