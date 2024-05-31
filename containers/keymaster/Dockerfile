FROM ktools/kcore-baseline:live

RUN apk -U add py3-cryptography

EXPOSE 4444

COPY files /

RUN /prep     # Hardening

HEALTHCHECK --interval=60s --timeout=3s --retries=3 CMD wget --no-check-certificate -q -O - https://127.0.0.1:4444/healthz | grep 'ok' || exit 1

USER km
WORKDIR /home/km
ENTRYPOINT ["/etc/init"]
