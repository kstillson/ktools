FROM ktools/kcore-baseline:live

RUN apk -U add python3

EXPOSE 8080

COPY files /

RUN /prep

USER watch
WORKDIR /home/watch
ENTRYPOINT ["/home/watch/filewatch"]
