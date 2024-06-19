FROM ktools/kcore-baseline:live

RUN apk -U add squid

EXPOSE 3128

COPY files /

RUN /prep

HEALTHCHECK --interval=60s --timeout=5s --retries=3 CMD nc -nzv -w 3 127.0.0.1 3128 || exit 1

USER squid
ENTRYPOINT ["/etc/init"]
