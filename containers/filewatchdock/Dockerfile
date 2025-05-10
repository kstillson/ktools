FROM ktools/kcore-baseline:live

EXPOSE 8080

COPY files /

RUN /prep

USER watch
WORKDIR /home/watch

ENTRYPOINT ["/etc/init"]
