#!/bin/bash
# Usage:  bash add-user.sh owner          (adds a user, or changes their password)
#         bash add-user.sh --remove owner
#         bash add-user.sh --list
cd "$(dirname "$0")"
case "$1" in
  --remove) sudo docker compose run --rm --no-deps web python -m app.users remove "$2" ;;
  --list)   sudo docker compose run --rm --no-deps web python -m app.users list ;;
  "")       echo "Please add a user name, for example:  bash add-user.sh owner"; exit 1 ;;
  *)        sudo docker compose run --rm --no-deps web python -m app.users add "$1" ;;
esac
