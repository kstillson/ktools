FROM ktools/kcore-baseline:live

# git (and openssh-client) are for cgi-bin/rc
RUN apk add apache2 apache2-proxy apache2-ssl git nagios nagios-web openssh-client py3-urllib3 ssmtp

EXPOSE 8080 8443

COPY files /

RUN /prep

USER apache
ENTRYPOINT ["/usr/sbin/httpd"]
CMD ["-e", "INFO", "-DFOREGROUND"]
