#!/bin/sh
# Makes a self-signed certificate the first time the proxy starts.
# To use a certificate from your own CA later, replace server.crt and server.key
# in the certs folder and restart (see the install guide).
set -e
CERTS=/etc/nginx/certs
NAME="${CERT_NAME:-billing-dashboard}"
if [ ! -f "$CERTS/server.crt" ] || [ ! -f "$CERTS/server.key" ]; then
  echo "No certificate found; creating a self-signed one for $NAME (valid 825 days)"
  mkdir -p "$CERTS"
  openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
    -keyout "$CERTS/server.key" -out "$CERTS/server.crt" \
    -subj "/CN=$NAME" -addext "subjectAltName=DNS:$NAME,DNS:localhost" >/dev/null 2>&1
  chmod 600 "$CERTS/server.key"
fi
