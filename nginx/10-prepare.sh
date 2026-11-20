#!/bin/sh
# Runs each time the proxy starts, before nginx.
#  1. Writes the nginx settings, so the http -> https redirect uses the right port.
#  2. Makes a self-signed certificate the first time.
#     To use a certificate from your own CA, replace server.crt and server.key
#     in the certs folder and restart (see INSTALL.md).
set -e

PORT="${HTTPS_PORT:-443}"
case "$PORT" in
  ''|*[!0-9]*) echo "HTTPS_PORT must be a number (got '$PORT'); using 443"; PORT=443 ;;
esac
if [ "$PORT" = "443" ]; then SUFFIX=""; else SUFFIX=":$PORT"; fi
sed "s/__HTTPS_PORT_SUFFIX__/$SUFFIX/" /etc/nginx/default.conf.template > /etc/nginx/conf.d/default.conf
echo "Web page on https port $PORT"

CERTS=/etc/nginx/certs
NAME="${CERT_NAME:-partner-console}"
if [ ! -f "$CERTS/server.crt" ] || [ ! -f "$CERTS/server.key" ]; then
  echo "No certificate found; creating a self-signed one for $NAME (valid 825 days)"
  mkdir -p "$CERTS"
  openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
    -keyout "$CERTS/server.key" -out "$CERTS/server.crt" \
    -subj "/CN=$NAME" -addext "subjectAltName=DNS:$NAME,DNS:localhost" >/dev/null 2>&1
  chmod 600 "$CERTS/server.key"
fi
