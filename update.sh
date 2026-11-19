#!/bin/bash
# Gets the latest version from GitHub and restarts. Your data and settings are kept.
set -e
cd "$(dirname "$0")"
git pull
# Logos must be readable by the dashboard (some servers make new files owner-only)
mkdir -p branding && chmod -R a+rX branding
# Keep the settings (Sophos secret), data and certificate key private
chmod 600 .env 2>/dev/null || true
sudo chmod 700 data certs 2>/dev/null || true
# --pull also fetches the latest security patches for the base images
sudo docker compose build --pull
sudo docker compose up -d
echo "Updated and restarted."
