# Security

- Treat customer text, knowledge documents and model output as untrusted.
- Keep human approval for refunds, account/security changes and outbound communication.
- Terminate TLS at the gateway. The app enforces JWT/API-key authentication, tenant-aware authorization and production HSTS responses.
- Store secrets in a managed secret store, rotate on exposure, and never include them in logs or images.
- Run the pinned non-root image with read-only filesystem, dropped capabilities and restricted bind addresses.
- Review `pip-audit`, Bandit and Trivy findings before release; pin image digests in production.
- Encrypt backups with `age`, separate encrypted data from identity keys, test restore quarterly and define retention by policy.

The health endpoint and API documentation disclose service metadata. Restrict them at the gateway if necessary. Production uses PostgreSQL; require encrypted network paths outside the private Compose network and use the recovery controls in `docs/database.md`.

PostgreSQL `audit_logs` uses forced, fail-closed tenant RLS. `auth_users`, `api_keys` and `refresh_sessions` are deliberate RLS exceptions because authentication runs before tenant context exists; repository access is narrowly bounded by tenant plus user/session identifiers and never exposes broad queries or raw token material.
