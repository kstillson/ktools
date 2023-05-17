FROM ktools/kcore-baseline:live

RUN apk -U add py3-pytest

EXPOSE 8080

COPY files /

RUN /prep

USER watch
WORKDIR /home/watch
CMD ["/home/watch/filewatch"]
