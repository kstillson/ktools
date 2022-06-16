FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache curl && \
    rm -rf /var/cache/apk/*

EXPOSE 1111

COPY files /

RUN /prep     # Hardening

ENV DEFAULT_RATE_LIMIT 2,120
ENV PB_LOG /var/log/homesec/pb-push.log
ENV RL_FILE /home/hs/data/pb.rl

USER hs
WORKDIR /home/hs
ENTRYPOINT ["/etc/init"]
