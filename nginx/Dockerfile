FROM nginx:1.27-alpine
RUN apk add --no-cache openssl
COPY nginx.conf /etc/nginx/conf.d/default.conf
# nginx runs every script in /docker-entrypoint.d before it starts
COPY 10-make-certificate.sh /docker-entrypoint.d/10-make-certificate.sh
RUN chmod +x /docker-entrypoint.d/10-make-certificate.sh
