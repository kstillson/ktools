FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache squid && \
    rm -rf /var/cache/apk/*

EXPOSE 3128

COPY files /

RUN /prep

USER squid
ENTRYPOINT ["/usr/sbin/squid"]
CMD ["--foreground"]
