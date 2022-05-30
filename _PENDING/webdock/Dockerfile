FROM ktools/kcore-baseline:live

# git (and openssh-client) are for cgi-bin/rc
RUN apk upgrade -U && \
    apk add --no-cache apache2 apache2-mod-wsgi apache2-proxy apache2-ssl git nagios nagios-web openssh-client php7-apache2 php7-cli php7-mysqli php7-zip php7-bz2 php7-dom php7-session php7-xml py3-django py3-mysqlclient py3-pip py3-urllib3 ssmtp && \
    rm -rf /var/cache/apk/*

EXPOSE 8080 8443

COPY files /

RUN pip3 install pushbullet.py

RUN /prep

USER apache
ENTRYPOINT ["/usr/sbin/httpd"]
CMD ["-e", "INFO", "-DFOREGROUND"]
