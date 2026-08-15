# Operations Runbook

## Daily checks

- Confirm `/health` returns HTTP 200 and `status=healthy`.
- Confirm `docker compose -f docker-compose.prod.yml ps` reports healthy services.
- Review Grafana availability, PostgreSQL/Redis exporter status, disk space and backup age.
- Use `/health` for process liveness and `/ready` for database readiness. Neither endpoint proves OpenAI or Redis availability.

## Application unavailable

1. Check `docker compose -f docker-compose.prod.yml ps` and app logs.
2. Check volume capacity and permissions for `/var/lib/nordly`.
3. Verify the deployed image digest and environment values without printing secrets.
4. Restart only the app: `docker compose -f docker-compose.prod.yml restart app`.
5. If the new release caused the issue, follow `docs/rollback.md`.

## Data corruption

1. Stop application writes: `docker compose -f docker-compose.prod.yml stop app`.
2. Preserve the failed volume before any repair attempt.
3. Restore into a new file/volume using `scripts/restore.*`; never overwrite the source.
4. Run `PRAGMA integrity_check`, start against the restored copy, then execute API smoke tests.

## Escalation

Page on-call for two-minute availability failures, suspected data loss, secret exposure or unsafe agent behavior. Record timestamps, image digest, scope, mitigations and customer impact.
