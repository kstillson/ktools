FROM ktools/kcore-baseline:live

RUN apk -U add git openssh

EXPOSE 22

COPY files /

RUN /prep

ENTRYPOINT ["/usr/sbin/sshd"]
CMD ["-D", "-e"]
