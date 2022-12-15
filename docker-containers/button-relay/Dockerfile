FROM ktools/kcore-baseline:live

RUN apk update -U && \
    apk add --no-cache bash python3 py3-pyserial tzdata && \
    rm -rf /var/cache/apk/*

# Needs apk tzdata:
ENV TZ America/New_York

EXPOSE 8080

COPY files /

RUN /prep

# Can't get permissions right using uid:relay  :-(
# USER relay

WORKDIR /home/relay
ENTRYPOINT ["/home/relay/button_relay"]
CMD ["--logfile", "/var/log/button_relay.log"]
