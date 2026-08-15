# Nordly Support Agent: Implementation Plan

This document is the execution plan for building the fictional Nordly CRM Oy
support operations agent from an empty project directory.

## Delivery Principles

- Build a working vertical slice early instead of creating an architecture-only skeleton.
- Keep customer data, subscriptions, incidents, tickets, and escalations in SQLite.
- Expose only narrow typed tools to the agent; never expose SQL execution.
- Keep probabilistic decisions in the agent and deterministic business rules in Python.
- Make demo mode fully offline and make all standard tests independent of OpenAI.
- Do not expose private chain-of-thought; expose only safe tool activity and evidence summaries.
- Do not implement irreversible external actions in version one.

## Phase 0: Repository Bootstrap

### Work

- Create the project structure under `app/`, `data/`, `knowledge_base/`, `tests/`,
  `evals/`, and `docs/`.
- Add `pyproject.toml`, `.env.example`, `.gitignore`, `Makefile`, `Dockerfile`,
  `docker-compose.yml`, `README.md`, `LICENSE`, and `AGENTS.md`.
- Configure Python 3.12+, FastAPI, Uvicorn, Pydantic v2, pydantic-settings,
  SQLite support, pytest, pytest-asyncio, Ruff, and OpenAI Agents SDK.
- Verify the current official OpenAI Agents SDK APIs before implementing the
  live runner.

### Exit criteria

- The package imports successfully.
- `python -m app.cli --help` works.
- `ruff check .` can run against the repository.

## Phase 1: Configuration, Domain Schemas, and Business Rules

### Work

- Implement `app/config.py` with environment-based settings.
- Implement enums and Pydantic models in `app/agent/schemas.py`.
- Add validation for email, text lengths, confidence, priority, and decision
  consistency.
- Create one canonical business-rules module for plans, features, escalation
  policy, and SLA values.
- Implement deterministic `calculate_sla_minutes(plan, priority)`.

### Exit criteria

- All plan/priority combinations return the documented SLA.
- Invalid confidence, priority, email, subject, and message values are rejected.
- No LLM output can override the calculated SLA.

## Phase 2: SQLite Database and Repositories

### Work

- Implement database initialization and migrations/schema creation.
- Add tables for customers, subscriptions, tickets, incidents, escalations,
  agent runs, tool events, and knowledge documents.
- Implement repositories for customers, tickets, incidents, subscriptions,
  escalations, and agent-run metadata.
- Add indexes and foreign-key constraints.
- Keep repository methods typed and bounded.

### Exit criteria

- A fresh SQLite database can be initialized repeatedly.
- Repository tests cover known and unknown records.
- No agent-facing API can enumerate unrelated customer records.

## Phase 3: Synthetic Nordly Dataset

### Work

- Implement an idempotent `data/seed.py`.
- Seed 20–30 fictional companies across European countries.
- Include Starter, Pro, and Business plans.
- Include active, trial, suspended, billing-hold, and cancelled accounts.
- Seed subscriptions, renewal dates, features, seats, and billing states.
- Seed active and historical incidents, including `INC-2041`.
- Seed 30–50 related historical support tickets.

### Exit criteria

- Seed data is clearly fictional.
- Demo customers and scenarios have internally consistent records.
- Running the seed command twice does not duplicate data.

## Phase 4: Knowledge Base and Search

### Work

- Create fictional Nordly Markdown documentation for authentication, billing,
  subscriptions, integrations, import/export, permissions, account security,
  and support policy.
- Implement a local deterministic search index in `app/tools/knowledge.py`.
- Return bounded results containing document name, section, snippet, and score.
- Add support for terms such as MFA, SSO, CSV encoding, invoices, refunds,
  seat limits, Outlook, Gmail, Slack, Zapier, and API access.

### Exit criteria

- Relevant queries retrieve the expected documentation.
- Search works without network access or embeddings.
- Search results can be cited in `SupportDecision.knowledge_sources`.

## Phase 5: Bounded Agent Tools

### Work

- Implement typed tools:
  - `get_customer_by_email(email)`
  - `get_subscription(customer_id)`
  - `get_account_status(customer_id)`
  - `search_knowledge_base(query)`
  - `check_active_incidents(product_area=None)`
  - `get_previous_tickets(customer_id, limit=5)`
- Add per-tool result limits and safe not-found responses.
- Add application-level tool event recording.
- Ensure customer-specific tools require the identified customer ID.
- Do not add generic SQL, customer enumeration, mutation, email, refund, or
  subscription-cancellation tools.

### Exit criteria

- Each tool has unit tests for normal, empty, and unauthorized-shaped inputs.
- Prompt injection cannot expand a tool's data scope.
- Tool outputs contain only information needed for support investigation.

## Phase 6: Guardrails and Support Decision Validation

### Work

- Write the Nordly-specific system prompt in `app/agent/prompts.py`.
- Treat all ticket content as untrusted customer input.
- Implement input guardrails for malformed, oversized, unrelated, and injection
  attempts.
- Implement deterministic post-processing in `app/agent/guardrails.py`.
- Enforce escalation for security, financial changes, severe data loss, low
  confidence, repeated unresolved issues, and confirmed technical incidents.
- Ensure reply drafts never claim that a prohibited action was completed.

### Exit criteria

- Security and refund scenarios cannot return an unsafe resolved response.
- Prompt injection is treated as ticket content and does not expose data.
- Structured decisions satisfy all conditional field requirements.

## Phase 7: Runner Abstraction and Offline Demo Agent

### Work

- Define a `SupportAgentRunner` protocol/interface.
- Implement `DemoSupportAgentRunner` with deterministic scenario handling.
- Return structured decisions, safe activity events, sources, and metadata.
- Mark all demo results explicitly as demo results.
- Support the required scenarios: outage, billing hold, CSV import, security,
  feature question, unknown customer, and prompt injection.

### Exit criteria

- Demo analysis requires no API key.
- Different scenarios produce different investigation paths.
- Results are suitable for API, CLI, UI, and offline evals.

## Phase 8: OpenAI Agents SDK Runner

### Work

- Implement `OpenAISupportAgentRunner` using the verified current SDK API.
- Register only the bounded Nordly tools.
- Configure structured `SupportDecision` output.
- Implement the actual dynamic tool-using loop.
- Add timeout, SDK error, malformed output, and unavailable-key handling.
- Enable Agents SDK tracing where supported without persisting private reasoning.

### Exit criteria

- Live mode is selected only when `DEMO_MODE=false`.
- The model can choose different tools for different tickets.
- Final output is validated before entering the service layer.
- No API key is printed or stored in repository data.

## Phase 9: Ticket Service and Persistence Workflow

### Work

- Implement `TicketService`.
- Create and persist incoming tickets.
- Invoke the selected runner.
- Validate and normalize the decision.
- Recalculate SLA deterministically.
- Store agent run metadata and tool activity.
- Create local escalation records when required.
- Support review, resolve, and escalate actions as local database updates only.

### Exit criteria

- Successful, escalated, missing-customer, and runner-error paths are handled.
- A ticket has a complete audit trail without hidden chain-of-thought.
- Escalation records contain team, priority, reason, summary, and timestamp.

## Phase 10: FastAPI API

### Work

- Implement `app/main.py` and `app/api/routes.py`.
- Add:
  - `GET /health`
  - `POST /api/v1/tickets`
  - `POST /api/v1/tickets/{ticket_id}/analyze`
  - `GET /api/v1/tickets`
  - `GET /api/v1/tickets/{ticket_id}`
  - `GET /api/v1/customers/{customer_id}`
  - `GET /api/v1/incidents`
  - `GET /api/v1/escalations`
  - `POST /api/v1/tickets/{ticket_id}/review`
- Use response models and consistent HTTP errors.
- Keep routes thin and delegate behavior to `TicketService`.

### Exit criteria

- Health, creation, analysis, listing, detail, incident, escalation, and review
  endpoints work against a seeded database.
- Invalid requests return useful validation errors.
- API tests use the demo runner and never call OpenAI.

## Phase 11: Internal Support Dashboard

### Work

- Build the inbox layout using HTML, CSS, and vanilla JavaScript.
- Add demo-mode banner and one-click scenario buttons.
- Display ticket details, customer, plan, account status, category, priority,
  SLA, confidence, and resolution status.
- Display safe high-level tool activity timeline.
- Display issue summary, diagnosis, evidence, recommended resolution, reply
  draft, escalation, and knowledge sources.
- Add local review, resolve, and escalate controls.
- Make the layout usable on desktop and mobile widths.

### Exit criteria

- A support employee can create or select a ticket and inspect its analysis.
- Timeline shows tools used without exposing private reasoning.
- Review actions visibly update the local demo state.

## Phase 12: CLI and Docker

### Work

- Implement `python -m app.cli analyze` using the same service layer.
- Add Docker image with Python 3.12+ and Uvicorn.
- Add Compose configuration with a persistent SQLite volume.
- Keep secrets outside the image and configure demo mode safely.

### Exit criteria

- CLI can analyze a ticket in demo mode.
- `docker compose up --build` starts the application.
- Data survives container restart through the configured volume.

## Phase 13: Evals and Test Suite

### Work

- Add at least 15 offline evaluation cases.
- Test known outage, individual login, billing hold, refund, security, CSV,
  API, unsupported feature, Business P1, Starter low priority, repeated issue,
  insufficient information, injection, and unknown customer.
- Add unit, service, API, security, and schema tests.
- Add regression tests for deterministic SLA and prohibited actions.

### Exit criteria

- All standard tests run without OpenAI.
- Offline evals report pass/fail per case and a final total.
- Failures are fixed before release rather than hidden or skipped.

## Phase 14: Documentation and Portfolio Readiness

### Work

- Complete `README.md` with business problem, architecture, setup, demo, live
  mode, agent behavior, and limitations.
- Add Mermaid architecture diagram in `docs/architecture.md`.
- Add fictional business case in `docs/business_case.md`.
- Add interview-oriented explanation in `docs/portfolio.md`.
- Add coding-agent guidance in `AGENTS.md`.
- Document security layers, human approval, deterministic SLA, and bounded tools.

### Exit criteria

- A new developer can run the demo from the README.
- Portfolio documentation explains why this is an agent rather than a chatbot.
- No unsupported real-world business metrics are claimed.

## Phase 15: Final Verification

Run the following from the project root:

```powershell
python -m data.seed
ruff format .
ruff check .
pytest
python evals/run_evals.py
$env:DEMO_MODE="true"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify manually:

- `GET /health` returns healthy status.
- Known outage discovers `INC-2041`, assigns P1, calculates Business SLA of 30 minutes,
  and recommends escalation.
- Security case escalates to Security without unsafe instructions.
- CSV case retrieves import/encoding documentation without unnecessary escalation.
- Prompt injection does not reveal unrelated customers.
- Billing hold does not claim that payment or account changes were performed.
- UI shows the complete safe investigation timeline and draft reply.

If `OPENAI_API_KEY` is available, run one live analysis with `DEMO_MODE=false`,
inspect tool events and validation, and report the result without printing secrets.
If no key is available, explicitly record that live execution was not tested.

## Final Deliverables

- Runnable FastAPI application.
- Offline demo mode with synthetic Nordly data.
- Real OpenAI Agents SDK runner.
- Bounded typed support tools.
- Deterministic SLA and escalation validation.
- SQLite persistence and local escalation records.
- Internal support dashboard.
- CLI.
- Docker support.
- Automated tests and offline evals.
- Architecture, business case, portfolio, README, and agent instructions.
