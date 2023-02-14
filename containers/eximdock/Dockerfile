FROM ktools/kcore-baseline:live

RUN apk -U add exim

EXPOSE 2525

COPY files /

RUN /prep

VOLUME ["/var/log", "/var/mail", "/var/spool"]

USER exim
ENTRYPOINT ["/usr/sbin/exim"]
CMD ["-bd", "-v", "-C", "/etc/exim/exim.conf"]
