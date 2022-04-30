FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache ssmtp supervisor syslog-ng && \
    rm -rf /var/cache/apk/*

EXPOSE 1514 
EXPOSE 1514/udp

COPY files /

RUN /prep

USER syslog
ENTRYPOINT ["/usr/bin/supervisord"]
CMD ["-n", "-c", "/etc/supervisord.conf"]
