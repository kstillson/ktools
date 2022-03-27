FROM kstillson/kds-baseline:live

RUN apk upgrade -U && \
    apk add --no-cache gnupg python3 && \
    rm -rf /var/cache/apk/*

EXPOSE 4443

COPY files /

RUN /prep     # Hardening

USER km
WORKDIR /home/km
ENTRYPOINT ["/home/km/km.py"]
