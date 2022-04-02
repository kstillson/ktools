FROM kstillson/kds-baseline:live

EXPOSE 8080

COPY files /

RUN /prep     # Hardening

USER hc
WORKDIR /home/hc
ENTRYPOINT ["/etc/init"]
