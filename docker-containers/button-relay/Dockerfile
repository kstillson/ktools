FROM ktools/kcore-baseline:live

RUN apk -U add bash python3 py3-pyserial tzdata

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
