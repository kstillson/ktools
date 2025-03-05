FROM ktools/kcore-baseline:live

RUN apk update && \
    apk upgrade && \
    apk add py3-pip && \
    python3 -m pip install dateparser ephem --break-system-packages

EXPOSE 8080

COPY files /

RUN /prep

USER atsvc
WORKDIR /home/atsvc
CMD ["/etc/init"]
