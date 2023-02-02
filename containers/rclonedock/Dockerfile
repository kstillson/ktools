FROM ktools/kcore-baseline:live

# Note: An extra init param will be required to select the mode.
# e.g.: d-run --extra-init {mode}

RUN apk -U add curl encfs fuse util-linux

COPY files /

RUN /prep

ENV TZ America/New_York

ENTRYPOINT ["/etc/init"]
CMD []
