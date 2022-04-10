FROM kstillson/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache gnupg && \
    rm -rf /var/cache/apk/*

EXPOSE 4444

COPY files /

RUN /prep     # Hardening

USER km
WORKDIR /home/km
ENTRYPOINT ["/etc/init"]
