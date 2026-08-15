# Billing Support Guide — Nordly CRM Oy

**Document owner:** Customer Success Engineering
**Last updated:** 2026-08-13
**Applies to:** All paid plans (Starter, Growth, Enterprise)

---

## 1. Failed Card Payments

### Automatic retry schedule
Nordly uses Stripe as the payment processor. Failed charges follow this retry cadence:

| Attempt | Timing | Customer notification |
|---|---|---|
| 1 | Due date | None (if fails) |
| 2 | +3 days | Email: "Payment failed — update card" |
| 3 | +5 days | Email + in-app banner |
| 4 | +7 days | Email: "Final notice" |

After the 4th failure, the account enters **Past Due** status. Data remains accessible for **14 additional days**, then the account is **suspended** (read-only for 7 days, then fully frozen).

### Common decline codes

| Stripe code | Meaning | Action |
|---|---|---|
| `card_declined` | Generic bank decline | Ask customer to call their bank, then retry |
| `insufficient_funds` | Balance too low | Retry after funds are available |
| `expired_card` | Card past expiry date | Update card in **Billing → Payment Methods** |
| `incorrect_cvc` | Security code mismatch | Re-enter CVC; if persists, use a different card |
| `processing_error` | Stripe processor error | Retry after 1 hour; escalate if repeated |
| `authentication_required` | 3D Secure needed | Customer must complete bank auth in-app |

### Updating payment details
1. **Admin Console → Billing → Payment Methods → Add Card**.
2. Nordly does **not** store raw card numbers; Stripe tokenises them.
3. Primary cards can be switched; old cards remain as backups unless deleted.

### Manual payment (Enterprise only)
- Enterprise customers on annual contracts may request invoice payment via bank transfer.
- Contact `billing@nordlycrm.fi` with PO number.
- Manual payment must clear before the invoice due date to avoid service interruption.

---

## 2. Overdue Invoices

### Grace period workflow
1. **Day 0** — Invoice due.
2. **Day 3** — Retry + email.
3. **Day 7** — Retry + email + banner.
4. **Day 14** — Final retry + email.
5. **Day 21** — Account **Past Due**; features restricted (no new imports, no API writes).
6. **Day 35** — Account **Suspended**; read-only access.
7. **Day 42** — Account **Frozen**; data retained for 90 days then scheduled for deletion.

### Reactivation after suspension
1. Customer updates payment method or pays outstanding balance.
2. System automatically retries outstanding invoices.
3. On success, account status returns to **Active** within 5 minutes.
4. If frozen, a Support ticket is required to initiate reactivation review (fraud check).

### Waiving late fees
Nordly does **not** charge late fees. However, if a customer disputes a chargeback, a **€15 chargeback fee** (per Stripe terms) is passed to the customer unless the chargeback is withdrawn.

---

## 3. VAT & Tax

### EU VAT
- Nordly CRM Oy is registered for VAT in Finland (FI30924658).
- Finnish customers: **24% VAT** applied automatically.
- EU business customers (VIES-registered): VAT is **reverse-charged** if a valid VAT ID is provided in **Billing → Tax Settings**.
- EU consumers: VAT charged at the rate of their member state (MOSS).

### Non-EU customers
- **United States:** sales tax applied based on billing address state (where required by local law).
- **Other countries:** generally no VAT; local tax obligations are the customer's responsibility.

### VAT invoices
- Every invoice is a VAT invoice by default (Finnish requirement).
- VAT ID appears on the invoice if supplied during checkout.

### Updating tax details
1. **Admin Console → Billing → Tax Settings**.
2. Enter VAT ID; system validates via VIES in real time.
3. If VIES is down, manual verification may take 1 business day.

---

## 4. Invoice Downloads

### Self-service
- **Admin Console → Billing → Invoices**.
- PDFs can be downloaded for all historical invoices.
- Invoices include: line items, tax breakdown, Nordly VAT ID, customer billing address, and Stripe receipt URL.

### Bulk export
- Enterprise customers may request a ZIP of all invoices via `billing@nordlycrm.fi`.
- Turnaround: 2 business days.

### Invoice corrections
- If a billing address or PO number is wrong, Admins can edit it for **future** invoices only.
- **Past invoices cannot be modified.** A credit note can be issued instead.
- Credit note requests go to `billing@nordlycrm.fi`; allow 3 business days.

---

## 5. Refund Policy

- **Monthly plans:** no refunds for partial months.
- **Annual plans:** prorated refund if cancelled within 30 days of purchase.
- **After 30 days:** no refund, but remaining time can be transferred to another Nordly organisation (Admin request required).
- **Overcharges or duplicate charges:** full refund processed within 5–10 business days.

---

## 6. Internal Notes & Escalation

- Do **not** share Stripe dashboard links with customers.
- Do **not** promise refunds outside the policy without Tier 2 approval.
- Escalate to **Tier 2 / Billing Team** if:
  - Chargeback is initiated.
  - Customer requests a custom contract or non-standard terms.
  - Tax exemption certificate needs review (US non-profits, etc.).
