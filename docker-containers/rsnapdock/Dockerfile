FROM ktools/kcore-baseline:live

RUN apk -U add curl expect openssh-client rsnapshot

COPY files /

RUN /prep

ENTRYPOINT ["/etc/init"]
CMD []
