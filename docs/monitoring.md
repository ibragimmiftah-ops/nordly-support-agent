# Monitoring

Prometheus scrapes `/metrics/` with the bearer credential read from `metrics_token.txt`, probes `/ready` through blackbox exporter, and scrapes PostgreSQL and Redis exporters. Grafana provisions the Prometheus datasource and the `Nordly production overview` dashboard.

Alertmanager is included with `local-log-only`, an intentionally empty default receiver. Alerts are visible in Prometheus and Alertmanager but no person is notified until an external receiver is configured and tested.

## External notifications

Configure Alertmanager with either a secret-backed `webhook_configs` URL or `email_configs` plus real SMTP credentials. Keep credentials outside Git, mount the rendered config read-only, run `amtool check-config alertmanager.yml`, send a controlled test alert, and verify receipt and resolution. Provider delivery is external and must not be treated as guaranteed.

## Alerts

- `NordlyAppDown`: `/ready` fails for two minutes.
- Exporter failures: warning after five minutes.
- PostgreSQL connections and Redis memory: sustained utilization warnings.
- `EscalationSpike`: `nordly_ticket_escalations_total` exceeds the threshold and prior-window comparison.

Rotate the metrics token by updating the secret file and recreating app and Prometheus. Keep monitoring ports loopback-bound or behind authenticated network controls.
