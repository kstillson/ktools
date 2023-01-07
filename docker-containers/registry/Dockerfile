
# TODO: can we start from kcore_baseline to inherit hardening...?
FROM docker.io/registry:2

RUN apk -U add bash apache2-utils

COPY files /

COPY files/etc/private.d/* /etc/

ENV TZ America/New_York
