FROM ktools/kcore-baseline:live

RUN apk -U add openssh rssh rsync rsyslog

EXPOSE 22

COPY files /

RUN /prep

CMD ["/etc/init"]
