FROM ktools/kcore-baseline:live

# git (and openssh-client) are for cgi-bin/rc
RUN apk upgrade -U && \
    apk add --no-cache apache2 apache2-proxy apache2-ssl git nagios nagios-web openssh-client py3-urllib3 ssmtp && \
    rm -rf /var/cache/apk/*

EXPOSE 8080 8443

COPY files /

RUN /prep

USER apache
ENTRYPOINT ["/usr/sbin/httpd"]
CMD ["-e", "INFO", "-DFOREGROUND"]
