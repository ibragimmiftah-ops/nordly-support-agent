#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 ENCRYPTED_BACKUP AGE_IDENTITY_FILE" >&2
  echo "Target is selected with PGHOST, PGPORT, PGDATABASE and PGUSER." >&2
  exit 2
fi

backup_file=$1
identity_file=$2
temporary_dump=$(mktemp "${TMPDIR:-/tmp}/nordly-restore.XXXXXX.dump")
trap 'rm -f "$temporary_dump"' EXIT HUP INT TERM

command -v pg_restore >/dev/null 2>&1 || { echo "pg_restore is required" >&2; exit 1; }
command -v age >/dev/null 2>&1 || { echo "age is required" >&2; exit 1; }
[ -f "$backup_file" ] || { echo "Backup not found: $backup_file" >&2; exit 1; }
[ -f "$identity_file" ] || { echo "Age identity not found: $identity_file" >&2; exit 1; }
[ "${CONFIRM_RESTORE:-}" = "RESTORE" ] || {
  echo "Set CONFIRM_RESTORE=RESTORE after confirming the target database is disposable." >&2
  exit 2
}
if [ -n "${PGPASSWORD_FILE:-}" ]; then
  export PGPASSWORD
  PGPASSWORD=$(cat "$PGPASSWORD_FILE")
fi

[ -f "$backup_file.sha256" ] && (
  cd "$(dirname "$backup_file")"
  sha256sum -c "$(basename "$backup_file").sha256"
)
age --decrypt --identity "$identity_file" --output "$temporary_dump" "$backup_file"
pg_restore --list "$temporary_dump" >/dev/null
pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges --dbname="${PGDATABASE:?PGDATABASE is required}" "$temporary_dump"
echo "PostgreSQL restore completed and archive structure verified: $PGDATABASE"
