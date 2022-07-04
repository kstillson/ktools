FROM ktools/kcore-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache python3 && \
    rm -rf /var/cache/apk/*

EXPOSE 8080

COPY files /

RUN /prep

USER watch
WORKDIR /home/watch
ENTRYPOINT ["/home/watch/filewatch"]
