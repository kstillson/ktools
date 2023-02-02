
# ---------- custom logic

all: local-rclone docker-all

# At time of writing, the version of rclone in Apline is 1.57, which only supports
# a version of "out of band oAuth" that is no longer supported by Google.  So we
# need to download the current version and use that instead.
# TODO: once 1.58 or beyond is available in Alpine, remove all this logic
# and just "apk add rclone" in the Dockerfile.
#
local-rclone: files/root/bin/rclone

files/root/bin/rclone:
	D=$(shell mktemp -d) && pushd . && cd $$D && wget https://downloads.rclone.org/v1.58.1/rclone-v1.58.1-linux-amd64.zip && unzip rclone-v1.58.1-linux-amd64.zip && popd && cp $$D/rclone-v1.58.1-linux-amd64/rclone $@ && rm -rf $$D



# ---------- pass-throughs

include ../../etc/Makefile-docker

comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
