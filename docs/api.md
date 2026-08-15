# API Operations

Interactive OpenAPI documentation is available at `/docs`; the schema is at `/openapi.json`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness only |
| POST | `/api/v1/tickets` | Create a ticket |
| POST | `/api/v1/tickets/{id}/analyze` | Analyze a ticket |
| GET | `/api/v1/tickets` | List tickets, maximum limit 100 |
| GET | `/api/v1/tickets/{id}` | Read a ticket |
| POST | `/api/v1/tickets/{id}/review` | Set a supported status |
| GET | `/api/v1/customers/{id}` | Read a customer |
| GET | `/api/v1/incidents` | List incidents |
| GET | `/api/v1/escalations` | List escalations |

There is currently no authentication or authorization middleware. Do not expose the service directly to the public internet; place it behind an authenticated gateway and rate limiting. Ticket fields are untrusted input and may contain personal data.
