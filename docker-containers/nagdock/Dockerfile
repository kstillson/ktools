FROM ktools/kcore-baseline:live

# iputils for a real (setuid) version of ping

RUN addgroup -g 360 nagios && \
    adduser -u 360 -G nagios -h /var/nagios -H -D nagios &&\
    apk upgrade -U && \
    apk add --no-cache curl iputils mailx nagios nagios-plugins nagios-plugins-dhcp nagios-plugins-disk nagios-plugins-disk_smb nagios-plugins-dns nagios-plugins-dummy nagios-plugins-http nagios-plugins-mysql nagios-plugins-ping nagios-plugins-smtp nagios-plugins-ssh nagios-plugins-swap nagios-plugins-tcp nagios-plugins-users ssmtp && \
    rm -rf /var/cache/apk/*

COPY files /

RUN /prep

USER nagios
ENTRYPOINT ["/etc/init"]
