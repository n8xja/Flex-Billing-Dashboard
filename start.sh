#!/bin/bash
# Builds (if needed) and starts the dashboard. It also starts by itself after a reboot.
set -e
cd "$(dirname "$0")"
if grep -q "paste-the-client" .env 2>/dev/null || [ ! -f .env ]; then
  echo "The Sophos API ID and secret are not in .env yet. Run bash setup.sh, then: nano .env"
  exit 1
fi
# Logos must be readable by the dashboard (some servers make new files owner-only)
mkdir -p branding && chmod -R a+rX branding
# Keep the settings (Sophos secret), data and certificate key private
chmod 600 .env 2>/dev/null || true
sudo chmod 700 data certs 2>/dev/null || true
sudo docker compose up -d --build

setting() { v=$(grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d '"'"'"' '); echo "${v:-$2}"; }
PORT=$(setting HTTPS_PORT 443)
ADDR=$(setting LISTEN_ADDRESS "$(hostname -I | awk '{print $1}')")
[ "$PORT" = "443" ] && SUFFIX="" || SUFFIX=":$PORT"
echo
echo "Started. Open https://$ADDR$SUFFIX in a web browser."
echo "Can't reach it from another computer? Run:  bash open-firewall.sh"
echo "The first data collection takes about 10 to 15 minutes."
