# Rollback

1. Stop writes and capture the current image digest and encrypted database backup.
2. Set `APP_IMAGE` to the last known-good immutable digest.
3. Run `docker compose -f docker-compose.prod.yml up -d --no-build --wait app`.
4. Verify `/health` and a read-only API request.
5. Restore data only when a migration or corruption requires it. Restore to a new volume, verify integrity, then switch volumes during a maintenance window.

The initial Alembic migration has a destructive downgrade and must never be used as a routine rollback. Prefer forward fixes. Production startup gates the app on `alembic upgrade head`; schema rollback requires a tested forward migration or restore into an isolated PostgreSQL instance before cutover.
