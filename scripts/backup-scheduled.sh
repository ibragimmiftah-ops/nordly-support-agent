#!/usr/bin/env sh
set -eu

interval=${BACKUP_INTERVAL_SECONDS:-86400}
case "$interval" in
  *[!0-9]* | "") echo "BACKUP_INTERVAL_SECONDS must be a positive integer" >&2; exit 2 ;;
esac
[ "$interval" -gt 0 ] || { echo "BACKUP_INTERVAL_SECONDS must be positive" >&2; exit 2; }

while true; do
  /usr/local/bin/nordly-backup
  sleep "$interval"
done
