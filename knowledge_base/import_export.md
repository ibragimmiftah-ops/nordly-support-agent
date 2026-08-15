# Import & Export Support Guide — Nordly CRM Oy

**Document owner:** Customer Success Engineering
**Last updated:** 2026-08-13
**Applies to:** All plans

---

## 1. CSV Import

### Supported entities
- Contacts
- Companies
- Deals
- Tasks
- Notes (as a column in Contact/Company/Deal import)

### File requirements

| Requirement | Specification |
|---|---|
| Format | CSV (comma-separated values) |
| Encoding | **UTF-8** (strongly recommended); UTF-8 BOM accepted; ISO-8859-1 may cause character corruption |
| Max file size | **20 MB** |
| Max rows per file | **50 000** |
| Header row | Required; must match field names or be mapped manually |
| Duplicate handling | Update existing (match by email / company domain) or Skip duplicates |

### Required fields

| Entity | Required fields | Notes |
|---|---|---|
| Contact | `email` | Must be valid email format; duplicates match on email |
| Company | `name` | Duplicates match on exact name |
| Deal | `name`, `stage` | `stage` must exist in the target pipeline |
| Task | `title`, `due_date` | `due_date` format: `YYYY-MM-DD` or ISO 8601 |

### Optional but common fields
- `first_name`, `last_name`, `phone`, `job_title`, `address`, `city`, `country`
- `company_id` or `company_name` — to link contact to company
- `owner_email` — assigns record to a specific Nordly user
- `tags` — semicolon-separated (e.g. `prospect;warm-lead`)
- `custom_field_slug` — use the internal field slug from **Settings → Custom Fields**

### Import procedure
1. Go to **Settings → Import & Export → Import**.
2. Choose entity type.
3. Upload CSV.
4. Map columns to Nordly fields (auto-mapping attempts exact name match).
5. Choose duplicate strategy.
6. Preview first 10 rows.
7. Click **Start Import**.

### Import status
- **Queued** → **Processing** → **Completed** or **Failed**
- Email notification sent to the user who started the import.
- Results CSV (with `nordly_id` and `status` columns) is available for download for 7 days.

### Common import errors

| Error | Cause | Resolution |
|---|---|---|
| "Invalid encoding detected" | File saved as Windows-1252 or Mac Roman | Re-save as UTF-8 in Excel, Google Sheets, or LibreOffice |
| "Row 245: Invalid email format" | Malformed email in data | Fix source data; results CSV lists all failed rows |
| "Row 512: Stage 'Closed-Won' not found" | Pipeline stage name mismatch | Verify exact stage name in **Settings → Pipelines** |
| "Row 89: User 'lea@nordly.fi' not found" | Owner email does not exist in org | Add user first, or leave blank to assign to importer |
| "File exceeds 20 MB" | Too many rows or large text fields | Split into multiple files |
| "Import timed out" | Very large file during peak hours | Retry during off-peak; split file; or request assisted import (Enterprise) |

---

## 2. Export Procedures

### Self-service export
1. **Settings → Import & Export → Export**.
2. Choose entity and filter (e.g. all contacts created this month).
3. Choose format: **CSV** or **JSON**.
4. Click **Request Export**.
5. Email arrives with a secure download link (valid 24 hours, one-time use).

### Export limits
- Max **100 000 records** per export request.
- Requests over the limit are queued as background jobs and may take up to 1 hour.
- Concurrent exports per organisation: **2**.

### Automated exports (Enterprise)
- Nightly SFTP drop or S3 push can be configured by Engineering.
- Contact CSM to set up.

### GDPR data export (Right to data portability)
- Any user can request a full account export via **Profile → Privacy → Download My Data**.
- Includes: profile, contacts owned, deals owned, tasks, notes, activity log.
- Delivery: ZIP file within 72 hours.
- Admin cannot block this request; it is a legal requirement.

---

## 3. Migration from Other CRMs

### Supported migration sources
- HubSpot (CSV export + native mapping template)
- Pipedrive (CSV export + native mapping template)
- Salesforce (CSV export; custom mapping required)
- Zoho CRM (CSV export)

### Migration templates
- Available in **Settings → Import & Export → Templates**.
- Templates reformat source CSV headers to Nordly field slugs.

### Assisted migration (Enterprise)
- CSM schedules a migration call.
- Engineering performs the import via secure temporary API key.
- Typical turnaround: 3–5 business days after receiving clean data.

---

## 4. Internal Notes & Escalation

- Do **not** accept customer CSVs via email for security; use secure upload or support ticket attachment (scan-enabled).
- Do **not** run imports on behalf of customers on non-Enterprise plans (self-service only).
- Escalate to **Tier 2 / Engineering** if:
  - Import repeatedly fails with "Unknown system error".
  - Customer requires a custom field type not supported in import (e.g. multi-select lookup).
  - GDPR export is not generated within 72 hours.
