FROM ktools/kcore-baseline:live

RUN apk -U add dnsmasq

EXPOSE 53 67

COPY files /

RUN /prep

ENTRYPOINT ["/usr/sbin/dnsmasq"]
CMD ["--conf-file=/etc/dnsmasq/dnsmasq.conf", "--keep-in-foreground", "--user=dnsmasq"]
