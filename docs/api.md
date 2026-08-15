# API Operations

Interactive OpenAPI documentation is available at `/docs`; the schema is at `/openapi.json`.

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| GET | `/health` | Liveness only | Public |
| GET | `/ready` | Database readiness | Public |
| POST | `/api/v1/auth/login` | Exchange credentials for JWT pair | Public |
| POST | `/api/v1/auth/refresh` | Rotate refresh token | Public |
| POST | `/api/v1/auth/logout` | Revoke refresh session | Public |
| POST | `/api/v1/tickets` | Create a ticket | Admin / Agent |
| POST | `/api/v1/tickets/{id}/analyze` | Analyze a ticket | Admin / Agent |
| GET | `/api/v1/tickets` | List tickets, maximum limit 100 | Any authenticated |
| GET | `/api/v1/tickets/{id}` | Read a ticket | Any authenticated |
| POST | `/api/v1/tickets/{id}/review` | Set a supported status | Admin / Agent |
| GET | `/api/v1/customers/{id}` | Read a customer | Any authenticated |
| DELETE | `/api/v1/gdpr/customers/{id}` | Erase customer data | Admin only |
| GET | `/api/v1/incidents` | List incidents | Any authenticated |
| GET | `/api/v1/escalations` | List escalations | Any authenticated |
| GET | `/metrics/` | Prometheus metrics | `X-Metrics-Token` or Bearer |

All `/api/v1` routes require JWT or API-key authentication. Requests are scoped to the authenticated tenant; cross-tenant access returns `404`. Rate limiting, security headers and PII redaction are enforced. Do not expose the service directly to the public internet; terminate TLS at the gateway.
