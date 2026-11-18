#!/bin/bash
# Opens the dashboard's ports (HTTPS_PORT and HTTP_PORT from .env) in the
# server's own firewall, so other computers can reach the web page.
#   Rocky / AlmaLinux / Red Hat: firewalld (firewall-cmd)
#   Ubuntu: ufw
# Safe to run more than once. To close a port you no longer use:
#   bash open-firewall.sh --close 8443
cd "$(dirname "$0")"

setting() {  # read a setting from .env, without quotes; $2 is the default
  local v
  v=$(grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')
  echo "${v:-$2}"
}
HTTPS_PORT=$(setting HTTPS_PORT 443)
HTTP_PORT=$(setting HTTP_PORT 80)

for p in "$HTTPS_PORT" "$HTTP_PORT" ${2:+"$2"}; do
  case "$p" in ''|*[!0-9]*) echo "'$p' is not a port number. Check .env."; exit 1 ;; esac
done

if command -v firewall-cmd >/dev/null 2>&1 && sudo firewall-cmd --state >/dev/null 2>&1; then
  if [ "$1" = "--close" ]; then
    sudo firewall-cmd --permanent --remove-port="$2/tcp"
    # Step 4A of INSTALL.md opens 443 and 80 by service name; close those too
    [ "$2" = "443" ] && sudo firewall-cmd --permanent --remove-service=https
    [ "$2" = "80" ] && sudo firewall-cmd --permanent --remove-service=http
  else
    sudo firewall-cmd --permanent --add-port="$HTTPS_PORT/tcp"
    sudo firewall-cmd --permanent --add-port="$HTTP_PORT/tcp"
  fi
  sudo firewall-cmd --reload
  echo
  echo "The firewall now allows these ports:"
  sudo firewall-cmd --list-ports
  sudo firewall-cmd --list-services | tr ' ' '\n' | grep -E '^https?$' | sed 's/^http$/80\/tcp (as the http service)/; s/^https$/443\/tcp (as the https service)/'
elif command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
  if [ "$1" = "--close" ]; then
    sudo ufw delete allow "$2/tcp"
  else
    sudo ufw allow "$HTTPS_PORT/tcp"
    sudo ufw allow "$HTTP_PORT/tcp"
  fi
  sudo ufw status
else
  echo "No active firewall found on this server (firewalld or ufw), so nothing needs opening."
  echo "If you still can't reach the page, ask your network team whether port $HTTPS_PORT is blocked between your computer and the server."
fi
