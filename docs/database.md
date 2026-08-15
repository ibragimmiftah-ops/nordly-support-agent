# Database and Recovery

## Production store

Production Compose uses PostgreSQL. SQLite remains a local development option only. The `migrate` service runs `alembic upgrade head` after PostgreSQL is healthy; the app starts only after that one-shot service succeeds. Do not run destructive downgrades in production.

## Encrypted logical backups

`scripts/backup.sh` and `scripts/backup.ps1` create PostgreSQL custom-format `pg_dump` archives, verify the archive catalog with `pg_restore --list`, encrypt with an `age` recipient, write SHA-256 checksums and remove artifacts older than `BACKUP_RETENTION_DAYS`. Store the age identity separately and off-host.

```bash
docker compose -f docker-compose.prod.yml --profile backup run --rm backup
docker compose -f docker-compose.prod.yml --profile scheduled-backup up -d backup-scheduled
```

The bind-mounted backup directory must itself be replicated to encrypted, access-controlled off-host storage. A local backup directory or WAL volume does not protect against host loss.

## Restore drill

Restore only to a disposable isolated database. The command verifies the encrypted checksum, decrypts the archive, verifies its catalog, and runs `pg_restore --exit-on-error`:

```bash
PGHOST=restore-db PGDATABASE=nordly_restore PGUSER=nordly \
PGPASSWORD_FILE=/run/secrets/postgres_password CONFIRM_RESTORE=RESTORE \
scripts/restore.sh backups/nordly-postgresql-TIMESTAMP.dump.age /secure/off-host/age-key.txt
```

After restore, run `alembic current`, application backend tests and representative read-only API checks. Record elapsed time and recovered backup age. A backup job succeeding is not evidence that the documented RTO or RPO was achieved.

## Recovery objectives and PITR

Initial operational targets are RPO 24 hours and RTO 4 hours for logical backups. They are targets, not guarantees, until repeated restore drills demonstrate them.

For lower RPO, use managed PostgreSQL PITR or implement scheduled `pg_basebackup` plus continuous WAL archiving to encrypted immutable off-host object storage. Monitor archive continuity, retention and restore capability. The Compose local WAL archive is only staging for off-host shipping; this repository does not implement or claim a verified PITR pipeline.
