FROM ktools/kcore-baseline:live

RUN apk -U add ssmtp supervisor syslog-ng

EXPOSE 1514 
EXPOSE 1514/udp

COPY files /

RUN /prep

HEALTHCHECK --interval=60s --timeout=5s --retries=3 CMD nc -nzv -w 3 127.0.0.1 1514 || exit 1

USER syslog
ENTRYPOINT ["/usr/bin/supervisord"]
CMD ["-n", "-c", "/etc/supervisord.conf"]
