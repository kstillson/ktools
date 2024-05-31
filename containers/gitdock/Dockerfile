FROM ktools/kcore-baseline:live

RUN apk -U add git openssh

EXPOSE 22

COPY files /

RUN /prep

HEALTHCHECK --interval=60s --timeout=3s --retries=3 CMD nc -nzv -w 3 127.0.0.1 22 || exit 1

ENTRYPOINT ["/usr/sbin/sshd"]
CMD ["-D", "-e"]
