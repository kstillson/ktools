FROM ktools/kcore-baseline:live

RUN apk -U add py3-cryptography

EXPOSE 4444

COPY files /

RUN /prep     # Hardening

USER km
WORKDIR /home/km
ENTRYPOINT ["/etc/init"]
