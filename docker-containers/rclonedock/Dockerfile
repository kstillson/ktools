FROM ktools/kcore-baseline:live

# Note: An extra init param will be required to select the mode.
# e.g.: d-run --extra_init {mode}


RUN apk upgrade -U && \
    apk add --no-cache curl encfs fuse util-linux && \
    rm -rf /var/cache/apk/*

COPY files /

RUN /prep

ENV TZ America/New_York

ENTRYPOINT ["/etc/init"]
CMD []
