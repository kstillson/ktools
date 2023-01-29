FROM ktools/kcore-baseline:live

RUN apk -U add ssmtp supervisor syslog-ng

EXPOSE 1514 
EXPOSE 1514/udp

COPY files /

RUN /prep

USER syslog
ENTRYPOINT ["/usr/bin/supervisord"]
CMD ["-n", "-c", "/etc/supervisord.conf"]
