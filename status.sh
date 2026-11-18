#!/bin/bash
# Shows whether everything is running, and the last messages from the data collector.
cd "$(dirname "$0")"
sudo docker compose ps
echo
echo "---- Last 20 lines from the data collector ----"
sudo docker compose logs --tail 20 collector
