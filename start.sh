#!/bin/bash
# Builds (if needed) and starts the dashboard. It also starts by itself after a reboot.
set -e
cd "$(dirname "$0")"
if grep -q "paste-the-client" .env 2>/dev/null || [ ! -f .env ]; then
  echo "The Sophos API ID and secret are not in .env yet. Run bash setup.sh, then: nano .env"
  exit 1
fi
sudo docker compose up -d --build
echo
echo "Started. Open https://$(hostname -I | awk '{print $1}') in a web browser."
echo "The first data collection takes about 10 to 15 minutes."
