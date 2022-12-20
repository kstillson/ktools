FROM ktools/kcore-baseline:live

RUN apk -U add squid

EXPOSE 3128

COPY files /

RUN /prep

USER squid
ENTRYPOINT ["/usr/sbin/squid"]
CMD ["--foreground"]
