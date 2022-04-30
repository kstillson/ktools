FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache exim && \
    rm -rf /var/cache/apk/*

EXPOSE 2525

COPY files /

RUN /prep

VOLUME ["/var/log", "/var/mail", "/var/spool"]

ENV TZ America/New_York

USER exim
ENTRYPOINT ["/usr/sbin/exim"]
CMD ["-bd", "-v", "-C", "/etc/exim/exim.conf"]
