FROM ktools/kcore-baseline:live

RUN apk -U add musl-locales openssh rssh rsync rsyslog

EXPOSE 22

COPY files /

RUN /prep

## HEALTHCHECK --interval=60s --timeout=3s --retries=3 CMD nc -nzv -w 3 127.0.0.1 22 || exit 1

CMD ["/etc/init"]
