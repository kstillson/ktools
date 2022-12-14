FROM docker.io/alpine:3.15

# python3 is for kmc

#    apk add --no-cache bash python3 py3-cryptography py3-pip py3-prometheus-client tzdata && \
#                                                     ^       ^

RUN umask 022 && \
    apk upgrade -U && \
    apk add --no-cache bash python3 py3-cryptography tzdata && \
    rm -rf /var/cache/apk/*

# Needs apk tzdata:
ENV TZ America/New_York

# Enable auto varz -> Prometheus
ENV KTOOLS_VARZ_PROM 1

COPY files /

# Run prep-local to perform limited baseline image hardneing.
RUN /prep-local

CMD ["/bin/bash"]
