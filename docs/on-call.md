# On-call Guide

## Severity

- SEV-1: data loss, broad outage, active secret compromise or unsafe consequential action.
- SEV-2: sustained degradation, escalation surge or dependency failure with customer impact.
- SEV-3: limited defect with workaround.

For SEV-1, acknowledge within 10 minutes, stop unsafe writes, page incident lead and security when relevant, and update stakeholders every 30 minutes. Preserve logs and backups without including ticket contents or secrets.

## Escalation spike

1. Validate the metric and compare ticket volume, category and destination team.
2. Check active incidents and model/provider degradation.
3. Switch to `DEMO_MODE=true` if provider behavior is suspect and safe offline behavior is acceptable.
4. Do not bulk-resolve or suppress escalations; human review remains required.
5. Record false positives and tune thresholds only after incident review.
