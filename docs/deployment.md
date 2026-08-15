# Deployment

## Prerequisites

- Docker Engine with Compose v2, TLS/restricted host access and sufficient persistent storage.
- Seven files under `secrets/`: `openai_api_key.txt`, `jwt_secret.txt`, `bootstrap_admin_password.txt`, `encryption_key.txt`, `metrics_token.txt`, `postgres_password.txt`, and `grafana_admin_password.txt`, mode 0600 where supported.
- `.env.production` based on `.env.example`; never commit it.
- An immutable `APP_IMAGE` tag or digest produced by CI.

## Procedure

1. Run CI and require quality, security, image build and staging smoke jobs to pass.
2. Trigger `workflow_dispatch` with production validation enabled and approve the GitHub production environment.
3. Pull the approved image and set `APP_IMAGE` to its immutable digest.
4. Run `docker compose -f docker-compose.prod.yml config --quiet`.
5. Run `docker compose -f docker-compose.prod.yml up -d --no-build --wait`; Compose runs the migration service before app startup.
6. Verify `/ready`, authenticated `/metrics/`, authentication and a non-consequential live-mode ticket flow.
7. Run and record the isolated PostgreSQL restore drill from `docs/database.md`.

Production always sets `DEMO_MODE=false`. Set both `BOOTSTRAP_ADMIN_USERNAME` and
`BOOTSTRAP_ADMIN_TENANT` only for the initial admin bootstrap; remove all bootstrap
settings after the account exists. Startup never creates demo credentials in production.

The manual CI production job starts the production Compose stack, waits for readiness and probes `/ready` and `/metrics/`; it does not access or deploy to production infrastructure.

GitHub Actions tags in CI are version tags rather than immutable SHAs. Pin each action to a reviewed full commit SHA before enforcing a high-assurance supply-chain policy, and record the corresponding release tag in a comment for maintainability.
