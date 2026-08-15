# Architecture

## Request flow

FastAPI routes call `TicketService`. The service creates a ticket, invokes the
configured runner, validates the resulting `SupportDecision`, calculates SLA
deterministically, stores audit data through repositories, and returns the
updated ticket.

## Modes

`DEMO_MODE=true` uses `DemoSupportAgentRunner`, which is deterministic and
offline. `DEMO_MODE=false` uses OpenAI Agents SDK 0.21.0 with typed
`SupportDecision` output and async `Runner.run`, and falls back to the safe demo
runner when the provider is unavailable.

## Boundaries

Repositories are the only persistence boundary. Tools expose narrow reads:
customer lookup, customer-scoped subscription/status/history, bounded incident
lookup, and local knowledge search. The agent cannot execute SQL or perform
consequential mutations.

Each live run receives a trusted context containing the authenticated tenant,
the customer ID verified by `TicketService`, and an audit event list. Tool
authorization never consumes a model-provided customer ID. SDK tools bind
tenant and customer scope from this context, label returned records as
untrusted data, and enforce configurable total and duplicate call limits.
Runs also have configurable turn and wall-clock limits. Provider token usage is
read from the SDK run context and recorded by `UsageService`.

## Data and operations

PostgreSQL stores production customers, subscriptions, account status, tickets, incidents,
escalations, agent runs, and tool events. `python -m data.seed` is deterministic
and idempotent. The dashboard is a static client of the public API and works
on desktop and mobile layouts. SQLite is retained for local development and tests.
