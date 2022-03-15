FROM docker.io/alpine:3.15

RUN apk upgrade -U && \
    apk add --no-cache bash curl tzdata && \
    rm -rf /var/cache/apk/*

COPY files /

# Run prep-local, not prep.  Prep is just there for other images to inherit.
RUN /prep-local

# Needs apk tzdata.
ENV TZ America/New_York

CMD ["/bin/bash"]

