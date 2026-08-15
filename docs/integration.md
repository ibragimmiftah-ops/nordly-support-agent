# Integration Guide

Integrators should use JSON over HTTPS through an authenticated gateway, set explicit connect/read timeouts and retry only idempotent reads. `POST` retries require an external idempotency strategy because the API does not accept idempotency keys.

No webhooks, email sender, refund mechanism, arbitrary SQL or account mutation tool exists. Consequential actions remain human-owned. In live mode, production Compose mounts the OpenAI key and other application secrets as files and passes their `_FILE` settings to the application.
