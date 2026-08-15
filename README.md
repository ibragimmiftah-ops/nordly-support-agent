# Nordly Support Agent

Nordly is a safety-oriented support-operations demo for a fictional European CRM. It provides deterministic offline ticket analysis, bounded customer-scoped tools, an optional OpenAI-backed runner, FastAPI/CLI interfaces and an operations dashboard.

## Local development

```bash
python -m pip install -e ".[dev]"
python -m data.seed
DEMO_MODE=true uvicorn app.main:app --reload
```

Open `http://localhost:8000/dashboard`; liveness is at `/health` and OpenAPI is at `/docs`.

```bash
python -m app.cli analyze --email "support@bergenlogistics.no" --subject "MFA help" --message "How do we enable MFA?"
```

## Containers

Local Compose continues to use the existing `docker-compose.yml`:

```bash
docker compose up --build
```

Staging smoke stack:

```bash
docker compose -f docker-compose.staging.yml up --build --wait
```

Production requires `.env.production` plus all secret files listed in `.env.example`. The migration service completes before the app starts:

```bash
docker compose -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.prod.yml up -d --build --wait
```

Production binds application and monitoring ports to loopback by default. Put an authenticated TLS gateway in front of the API. The image is multi-stage, non-root, includes Alembic assets, uses one Uvicorn worker for correct in-process Prometheus counters, and is designed for a read-only root filesystem.

## Dependencies and migrations

`requirements-production.txt` lists runtime and migration dependencies while `constraints.txt` pins their direct versions, including OpenAI Agents SDK 0.21.0. Install with `python -m pip install -r requirements-production.txt`. Regenerate constraints only after security/release review using the command documented at the top of `constraints.txt`.

Alembic covers both database backends, including tenant-scoped memory and provider usage. Use `alembic upgrade head`; existing schemas stamped at `0001` receive these tables through revision `0002`.

## Operations

- [Deployment](docs/deployment.md)
- [Operations runbook](docs/ops-runbook.md)
- [Rollback](docs/rollback.md)
- [Monitoring](docs/monitoring.md)
- [On-call](docs/on-call.md)
- [Database and recovery](docs/database.md)
- [API operations](docs/api.md)
- [Integration](docs/integration.md)
- [Security](docs/security.md)
- [SLA/SLO](docs/sla.md)
- [Known limitations](docs/limitations.md)
- [Architecture](docs/architecture.md)

## Persistence and cost controls

Local development defaults to SQLite, while production Compose uses PostgreSQL. Live provider usage and bounded redacted support memory are persisted per tenant. Configured rolling daily and weekly USD budgets fail over to deterministic analysis before a provider call. `/metrics` exposes aggregate usage and cost without tenant labels.

## Safety model

The LLM may classify a ticket, but Python calculates SLA values and applies guardrails. Security, refund, prompt-injection, low-confidence and other consequential cases require escalation or more information. Customer input is untrusted; tools cannot execute arbitrary SQL, send email, issue refunds or change account state.
