#!/usr/bin/env sh
set -eu

output_directory=${BACKUP_DIRECTORY:-${1:-}}
age_recipient=${AGE_RECIPIENT:-${2:-}}
retention_days=${BACKUP_RETENTION_DAYS:-30}

[ -n "$output_directory" ] && [ -n "$age_recipient" ] || {
  echo "Usage: BACKUP_DIRECTORY=... AGE_RECIPIENT=... $0" >&2
  exit 2
}
command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump is required" >&2; exit 1; }
command -v pg_restore >/dev/null 2>&1 || { echo "pg_restore is required" >&2; exit 1; }
command -v age >/dev/null 2>&1 || { echo "age is required" >&2; exit 1; }

if [ -n "${PGPASSWORD_FILE:-}" ]; then
  [ -r "$PGPASSWORD_FILE" ] || { echo "PGPASSWORD_FILE is not readable" >&2; exit 1; }
  export PGPASSWORD
  PGPASSWORD=$(cat "$PGPASSWORD_FILE")
fi

mkdir -p "$output_directory"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
temporary_dump=$(mktemp "${TMPDIR:-/tmp}/nordly-backup.XXXXXX.dump")
output_file="$output_directory/nordly-postgresql-$timestamp.dump.age"
trap 'rm -f "$temporary_dump"' EXIT HUP INT TERM

pg_dump --format=custom --no-owner --no-privileges --file="$temporary_dump"
pg_restore --list "$temporary_dump" >/dev/null
age --recipient "$age_recipient" --output "$output_file" "$temporary_dump"
sha256sum "$output_file" > "$output_file.sha256"

find "$output_directory" -type f \( -name 'nordly-postgresql-*.dump.age' -o -name 'nordly-postgresql-*.dump.age.sha256' \) \
  -mtime "+$retention_days" -delete
echo "Encrypted PostgreSQL backup created and source dump verified: $output_file"
