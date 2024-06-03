FROM ktools/kcore-baseline:live

RUN apk -U add curl

EXPOSE 1111

COPY files /

RUN /prep     # Hardening

ENV DEFAULT_RATE_LIMIT 2,120
ENV PB_LOG /var/log/homesec/pb-push.log
ENV RL_FILE /home/hs/data/pb.rl

## HEALTHCHECK --interval=60s --timeout=3s --retries=3 CMD wget -q -O - -T 3 http://127.0.0.1:1111/healthz | grep 'ok' || exit 1

USER hs
WORKDIR /home/hs
ENTRYPOINT ["/etc/init"]
