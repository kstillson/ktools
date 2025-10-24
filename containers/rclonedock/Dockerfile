FROM ktools/kcore-baseline:live

# Note: An extra init param will be required to select the mode.
# e.g.: d-run --extra-init {mode}

# coreutils for a fully-functional "date" cmnd
RUN apk -U add coreutils curl gocryptfs fuse rsync openssh-client rclone util-linux

COPY files /

RUN /prep

ENTRYPOINT ["/etc/init"]
CMD []
