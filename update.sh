#!/bin/bash
# Gets the latest version from GitHub and restarts. Your data and settings are kept.
set -e
cd "$(dirname "$0")"
git pull
# Logos must be readable by the dashboard (some servers make new files owner-only)
mkdir -p branding && chmod -R a+rX branding
sudo docker compose up -d --build
echo "Updated and restarted."
