FROM ktools/kcore-baseline:live

EXPOSE 8080

COPY files /

RUN /prep     # Hardening

USER hc
WORKDIR /home/hc
CMD ["/etc/init"]
