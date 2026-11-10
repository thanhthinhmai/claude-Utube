# Egress filter for learn jobs from YouTube (specs/007 tasks T031): an HTTP(S) proxy that only lets through
# the domains YouTube needs. Everything else is refused.
FROM alpine:3.20
RUN apk add --no-cache tinyproxy
COPY tinyproxy.conf allow.txt /etc/tinyproxy/
USER nobody
EXPOSE 8888
ENTRYPOINT ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
