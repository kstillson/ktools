FROM docker.io/alpine:3.15

# python3 is for kmc (copied in by ./Build)

RUN apk upgrade -U && \
    apk add --no-cache bash python3 tzdata && \
    rm -rf /var/cache/apk/*

ENV TZ America/New_York     # Needs apk tzdata.

COPY files /

# Run prep-local to perform limited baseline image hardneing.
RUN /prep-local

CMD ["/bin/bash"]

