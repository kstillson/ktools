FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache git openssh && \
    rm -rf /var/cache/apk/*

EXPOSE 22

COPY files /

RUN /prep

ENTRYPOINT ["/usr/sbin/sshd"]
CMD ["-D", "-e"]
