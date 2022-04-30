FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache openssh rssh rsync rsyslog && \
    rm -rf /var/cache/apk/*

EXPOSE 22

COPY files /

RUN /prep

CMD ["/etc/init"]
