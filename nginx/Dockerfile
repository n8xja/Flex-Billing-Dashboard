FROM nginx:1.29-alpine
RUN apk add --no-cache openssl
# The settings are written from this template at start-up (see 10-prepare.sh)
COPY default.conf.template /etc/nginx/default.conf.template
# nginx runs every script in /docker-entrypoint.d before it starts
COPY 10-prepare.sh /docker-entrypoint.d/10-prepare.sh
RUN chmod 644 /etc/nginx/default.conf.template && chmod 755 /docker-entrypoint.d/10-prepare.sh \
 && rm -f /etc/nginx/conf.d/default.conf
