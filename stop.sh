#!/bin/bash
cd "$(dirname "$0")"
sudo docker compose down
echo "Stopped. Your data is kept. Start again with bash start.sh"
