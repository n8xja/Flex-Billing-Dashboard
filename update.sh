#!/bin/bash
# Gets the latest version from GitHub and restarts. Your data and settings are kept.
set -e
cd "$(dirname "$0")"
git pull
sudo docker compose up -d --build
echo "Updated and restarted."
