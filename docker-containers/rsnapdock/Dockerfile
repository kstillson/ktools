FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache curl expect openssh-client rsnapshot && \
    rm -rf /var/cache/apk/*

COPY files /

RUN /prep

ENTRYPOINT ["/etc/init"]
CMD []
