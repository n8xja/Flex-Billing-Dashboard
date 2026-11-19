#!/bin/bash
# One-time preparation. Safe to run again.
set -e
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed yet. Please do the 'Install Docker' step in INSTALL.md first."
  exit 1
fi

mkdir -p data certs branding
# The dashboard runs as user number 1000 inside its container; let it write its data folder.
# Only that user can read it: it holds your customers' license and billing data.
sudo chown -R 1000:1000 data
sudo chmod 700 data
# The certificate's private key: readable by the server's administrator only
sudo chmod 700 certs

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created the settings file (.env)."
fi
chmod 600 .env

if grep -q "paste-the-client" .env; then
  echo
  echo "NEXT: put your Sophos API ID and secret into the settings file:"
  echo "      nano .env"
  echo "Then run:  bash start.sh"
else
  echo "Settings look filled in. Next run:  bash start.sh"
fi
