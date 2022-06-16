FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache py3-cryptography && \
    rm -rf /var/cache/apk/*

EXPOSE 4444

COPY files /

RUN /prep     # Hardening

USER km
WORKDIR /home/km
ENTRYPOINT ["/etc/init"]
