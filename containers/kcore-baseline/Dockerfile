FROM docker.io/alpine:3.17

##_prom MIGHT WANT TO ADD THIS TO THE APK LIST...:  py3-prometheus-client

RUN umask 022 && \
    ln -s /var/cache/apk /etc/apk/cache && \
    apk update && \
    apk cache -v sync && \
    apk upgrade && \
    apk add bash python3 py3-cryptography py3-requests tzdata

# Enable auto varz -> Prometheus
##_prom ENV KTOOLS_VARZ_PROM 1

COPY files /

# Run prep-local to perform limited baseline image hardneing.
RUN /prep-local

CMD ["/bin/bash"]
