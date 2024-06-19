FROM ktools/kcore-baseline:live

RUN apk -U add exim

EXPOSE 2525

COPY files /

RUN /prep

VOLUME ["/var/log", "/var/mail", "/var/spool"]

HEALTHCHECK --interval=60s --timeout=5s --retries=3 CMD nc -nzv -w 3 127.0.0.1 2525 || exit 1

USER exim
ENTRYPOINT ["/usr/sbin/exim"]
CMD ["-bd", "-v", "-C", "/etc/exim/exim.conf"]
