# Known Limitations

- SQLite and PostgreSQL are supported; production rate limiting is distributed through Redis. Redis-backed caching is not implemented.
- SQLite permits only one practical writable app replica and can contend under write load; use PostgreSQL for multi-replica production.
- TLS termination, idempotency keys and webhook delivery remain external or unimplemented.
- `/health` is a liveness check and does not verify database or provider readiness.
- Vector knowledge-base RAG is implemented. Per-customer support memory remains bounded lexical history; content is redacted, deduplicated and expires by policy.
- Budgets use rolling 24-hour and 7-day windows and configured static pricing; reconcile pricing when provider rates change.
- PostgreSQL schema changes are Alembic-managed; application startup validates the deployed revision and required tables without issuing DDL. SQLite development startup remains self-initializing.
- Production logical PostgreSQL backups provide restore points. PITR remains unverified until base backups and off-host WAL shipping are implemented and drilled.
- CI is implemented and validates tests, security checks, the production artifact and staging smoke behavior; production deployment remains an external operation.
- OpenAI Agents SDK 0.21.0 is wrapped with `asyncio.wait_for`; duplicate-call limits are enforced in trusted tool context.
- A timed-out remote request may continue provider transport cancellation cleanup, but its result is ignored and deterministic fallback uses the original run ID.
