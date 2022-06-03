FROM ktools/kcore-baseline:live

EXPOSE 8080

COPY files /

RUN /prep     # Hardening

USER hs
WORKDIR /home/hs
ENTRYPOINT ["/etc/init"]
