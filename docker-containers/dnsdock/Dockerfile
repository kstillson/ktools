FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache dnsmasq && \
    rm -rf /var/cache/apk/*

EXPOSE 53 67

COPY files /

RUN /prep

ENTRYPOINT ["/usr/sbin/dnsmasq"]
CMD ["--conf-file=/etc/dnsmasq/dnsmasq.conf", "--keep-in-foreground", "--user=dnsmasq"]
