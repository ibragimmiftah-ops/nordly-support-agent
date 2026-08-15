# SLA and SLO

The application computes ticket SLA deterministically in Python; operational service objectives are separate.

Proposed initial SLOs, subject to business approval:

- API availability: 99.9 percent monthly, measured by successful authenticated-gateway health probes.
- SEV-1 acknowledgement: 10 minutes; SEV-2: 30 minutes.
- Recovery point objective: 24 hours until backup frequency is automated and measured.
- Recovery time objective: 4 hours, validated by restore exercises.

No contractual SLA is provided by this repository. Current `/health` is liveness-only, so availability measurements do not prove dependency or data-store health.
