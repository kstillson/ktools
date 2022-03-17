FROM kstillson/kds-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache gnupg python2 && \
    rm -rf /var/cache/apk/*

EXPOSE 4443

COPY files /

RUN /prep

USER km
WORKDIR /home/km
ENTRYPOINT ["/home/km/km.py"]
