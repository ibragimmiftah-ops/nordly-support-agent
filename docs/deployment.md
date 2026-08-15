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
settings after the account exists. Startup never creates offline development credentials in production.

## Scaling and load balancing

The application is stateless: session state lives in signed JWTs and Redis, file storage is not used, and Prometheus counters are kept correct by running one Uvicorn worker per container. Horizontal scaling is supported through the following reference policy:

1. **Load balancer**: terminate TLS at the gateway and route to `APP_PORT` on any app replica. Sticky sessions are not required.
2. **Autoscaling**: scale on average CPU > 60% or request latency p95 > 1s over 5 minutes. Minimum 2 replicas, maximum 10. Scale down only when below threshold for 10 minutes.
3. **Health routing**: use `/health` for load balancer health checks and `/ready` for Kubernetes readiness. Do not route traffic to a replica that fails `/ready`.
4. **Database**: use a single PostgreSQL primary for writes. Reads can target a read replica only after repository support is added; the current connection wrapper uses one `DATABASE_URL`.
5. **Redis**: required for production rate limiting and optional caching (`REDIS_URL`, `CACHE_TTL_SECONDS`). Use a managed Redis or Sentinel/Cluster for availability.
6. **Monitoring**: aggregate per-replica Prometheus metrics through the gateway or a federated scrape target; each replica exposes `/metrics/` protected by `METRICS_TOKEN`.

See `docker-compose.prod.yml` for per-service CPU/memory limits and `docs/monitoring.md` for alert thresholds.

## Supply chain

GitHub Actions tags in CI are version tags rather than immutable SHAs. Pin each action to a reviewed full commit SHA before enforcing a high-assurance supply-chain policy, and record the corresponding release tag in a comment for maintainability.
