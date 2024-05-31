FROM ktools/kcore-baseline:live

RUN apk -U add dnsmasq

EXPOSE 53 67

COPY files /

RUN /prep

HEALTHCHECK --interval=60s --timeout=3s --retries=3 CMD nc -nzv -w 3 127.0.0.1 53 || exit 1

ENTRYPOINT ["/usr/sbin/dnsmasq"]
CMD ["--conf-file=/etc/dnsmasq/dnsmasq.conf", "--keep-in-foreground", "--user=dnsmasq"]
