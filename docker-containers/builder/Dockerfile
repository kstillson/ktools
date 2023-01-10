FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add bash git util-linux-misc make netavark ncurses openssh podman py3-yaml

COPY files /

RUN /prep

WORKDIR /root

CMD ["/etc/init"]
