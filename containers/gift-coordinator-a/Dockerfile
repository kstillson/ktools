FROM ktools/kcore-baseline:live

RUN apk -U add python3

EXPOSE 8080

COPY files /

RUN /prep

## HEALTHCHECK --interval=60s --timeout=3s --retries=3 CMD wget -q -O - -T 3 http://127.0.0.1:8080/healthz | grep 'ok' || exit 1"

USER santa
WORKDIR /home/santa
ENTRYPOINT ["/etc/init"]
