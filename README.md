# Nordly Support Agent

Nordly Support Agent is the production AI platform that powers Level 1 support operations at [Nordly](https://nordly.example), a European B2B CRM company. It ingests support tickets, enriches them with customer context and active incidents, and produces a validated `SupportDecision` for every request. The system separates probabilistic language-model output from deterministic business rules: the model may classify intent, but Python calculates SLA, applies guardrails, and decides whether a ticket can be resolved automatically or must be escalated.

The agent is built around safety and auditability. Customer ticket text is treated as untrusted input. Tools expose only narrow, read-only operations scoped to a single tenant and customer. Consequential actions such as refunds, account changes, outbound email, or database mutations always require human approval and are never exposed to the agent loop.

## Capabilities

- **Ticket analysis** — deterministic offline runner for development and testing; optional OpenAI-backed runner for production, with automatic fallback on timeout, budget exhaustion, or safety triggers.
- **Tenant isolation** — every business record is scoped to a tenant. PostgreSQL row-level security is enforced fail-closed in production.
- **Authentication and authorization** — JWT access/refresh tokens with rotation and revocation, bcrypt password hashing, and API keys for service-to-service calls. Role-based access control supports admin, agent, and viewer roles.
- **Cost and safety controls** — configurable per-run turn, tool-call, timeout, and duplicate-call limits; rolling daily and weekly USD budgets; atomic budget reservations.
- **Memory and RAG** — persistent, encrypted, tenant-scoped customer memory with deduplication and expiration; deterministic vector retrieval with versioned knowledge chunks and citations.
- **Observability** — structured JSON logs with correlation IDs and PII redaction; Prometheus metrics; optional OpenTelemetry tracing; health and readiness endpoints.
- **Operations** — production Docker Compose with PostgreSQL, Redis, Prometheus, Grafana, Alertmanager, encrypted backups, restore drills, and runbooks.

## Local development

```bash
python -m pip install -e ".[dev]"
python -m data.seed
DEMO_MODE=true uvicorn app.main:app --reload
```

Open `http://localhost:8000/dashboard`; liveness is at `/health`, readiness at `/ready`, and OpenAPI is at `/docs`.

```bash
python -m app.cli analyze --email "support@bergenlogistics.no" --subject "MFA help" --message "How do we enable MFA?"
```

## Containers

Local Compose uses `docker-compose.yml`:

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

The LLM may classify a ticket, but Python calculates SLA values and applies guardrails. Security, refund, prompt-injection, low-confidence, and other consequential cases require escalation or more information. Customer input is untrusted; tools cannot execute arbitrary SQL, send email, issue refunds, or change account state.
