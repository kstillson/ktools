FROM ktools/kcore-baseline:live

RUN apk -U add python3

EXPOSE 8080

COPY files /

RUN /prep

USER santa
WORKDIR /home/santa
ENTRYPOINT ["/etc/init"]
