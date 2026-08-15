# Integrations Support Guide — Nordly CRM Oy

**Document owner:** Customer Success Engineering
**Last updated:** 2026-08-13
**Applies to:** Growth and Enterprise (SSO requires Growth+)

---

## 1. Microsoft Outlook Integration

### What it does
- Sync emails and calendar events to Nordly contact/company timelines.
- Track email opens and clicks (optional, per-user setting).
- Create Nordly tasks from flagged Outlook emails.

### Setup
1. User goes to **Profile → Integrations → Microsoft Outlook → Connect**.
2. OAuth consent to Microsoft Graph scopes: `Mail.Read`, `Calendars.Read`, `User.Read`.
3. Admin-level consent is required for organisations with Azure AD conditional access.

### Common errors

| Error | Cause | Resolution |
|---|---|---|
| "Admin consent required" | Azure AD tenant blocks user consent | Admin must grant consent via Azure portal or Nordly Admin Console |
| "Token expired" | Refresh token revoked by Microsoft | Re-authenticate the integration |
| "Mailbox not found" | Shared mailbox or delegated access | Only primary mailboxes are supported; use SMTP forwarding workaround |
| "Rate limit exceeded" | Microsoft Graph throttling | Sync resumes automatically; large mailboxes may need batching (Enterprise feature) |

### Data sync frequency
- Email: near real-time (webhook push).
- Calendar: every 15 minutes (poll).
- Manual sync button available in **Integrations** panel.

### Revoking access
- User can disconnect in **Profile → Integrations**.
- Admin can force-disconnect for any user in **Admin Console → Integrations → Outlook**.

---

## 2. Gmail Integration

### What it does
- Sync emails and Google Calendar events to Nordly timelines.
- Send emails from Nordly using the user's Gmail address (via Gmail API).

### Setup
1. **Profile → Integrations → Gmail → Connect**.
2. Google OAuth scopes: `gmail.readonly`, `calendar.readonly`, `userinfo.email`.
3. If Google Workspace admin has restricted apps, Nordly must be whitelisted.

### Common errors

| Error | Cause | Resolution |
|---|---|---|
| "This app is blocked" | Workspace admin restriction | Admin adds Nordly to allowed apps in Google Admin Console |
| "Insufficient permissions" | User denied a scope during OAuth | Disconnect and reconnect, approving all scopes |
| "Token revoked" | User changed Google password or removed app | Re-authenticate |

### Sync frequency
- Email: near real-time (Gmail push notifications).
- Calendar: every 15 minutes.

---

## 3. Slack Integration

### What it does
- Notifications for deal stage changes, task assignments, and mentions.
- Slash commands: `/nordly search [contact]`, `/nordly deal [name]`.
- Unfurling: Nordly URLs posted in Slack show rich previews.

### Setup
1. **Admin Console → Integrations → Slack → Add to Slack**.
2. Authorise Nordly app to the desired workspace.
3. Choose a default channel for notifications.
4. (Optional) Map Nordly deal pipelines to specific Slack channels.

### Permissions required
- `chat:write` — post messages
- `commands` — slash commands
- `links:read`, `links:write` — URL unfurling
- `users:read` — match Slack users to Nordly users

### Common errors

| Error | Cause | Resolution |
|---|---|---|
| "Channel not found" | Bot was removed from channel or channel is private | Re-invite `@Nordly` bot to the channel |
| "Missing scope" | Workspace admin changed scopes | Re-install the app from Admin Console |
| "User mapping failed" | Slack email differs from Nordly email | Update email in one system or manually map in Admin Console |

### Notification settings
- Per-user: **Profile → Notifications → Slack**.
- Per-channel: Admin Console pipeline mappings.
- Do-not-disturb hours respect the user's Nordly profile timezone.

---

## 4. Zapier / API Concepts

### Zapier
- Nordly is available on Zapier as an **Invite-only** app.
- Access link is provided in **Admin Console → Integrations → Zapier**.
- Supported triggers: New Contact, New Deal, Deal Stage Changed, New Task.
- Supported actions: Create Contact, Create Deal, Create Note, Find Contact.

### Common Zapier issues
- **Zap not firing:** check trigger filter conditions; verify Nordly API key is active.
- **Duplicate records:** ensure Zap has a deduplication step (e.g. search before create).
- **Rate limit hit:** Growth = 1 000/min; if exceeded, Zaps may be throttled by Zapier.

### REST API
- Base URL: `https://api.nordlycrm.fi/v1`
- Authentication: `Authorization: Bearer nk_live_...`
- Rate limits: see Subscriptions guide.
- Pagination: `?page=1&per_page=100` (max 100).

### Webhooks (Growth+)
- Configure in **Admin Console → Developers → Webhooks**.
- Events: `contact.created`, `deal.updated`, `task.completed`, etc.
- Signature verification uses HMAC-SHA256 with a shared secret.
- Retry policy: 5 attempts with exponential backoff (1s, 2s, 4s, 8s, 16s).

### API error codes

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `bad_request` | Malformed JSON or missing field |
| 401 | `unauthorized` | Invalid or expired API key |
| 403 | `forbidden` | Key valid but lacks permission for this resource |
| 404 | `not_found` | Resource does not exist |
| 409 | `conflict` | Duplicate unique field (e.g. email) |
| 422 | `validation_error` | Business rule violation |
| 429 | `rate_limited` | Too many requests; retry after `Retry-After` header |
| 500 | `internal_error` | Server error; retry with backoff and open ticket if persistent |

---

## 5. Internal Notes & Escalation

- Do **not** share API secrets in chat.
- Do **not** enable beta integrations for production orgs without consent.
- Escalate to **Tier 2 / Engineering** if:
  - OAuth token refresh loops continuously.
  - Webhooks are not delivering despite healthy endpoint (check HMAC verification).
  - Microsoft/Google API changes break sync for multiple customers.
