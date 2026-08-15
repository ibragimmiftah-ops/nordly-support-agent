# Subscriptions Support Guide — Nordly CRM Oy

**Document owner:** Customer Success Engineering
**Last updated:** 2026-08-13
**Applies to:** Starter, Growth, Enterprise plans

---

## 1. Plan Overview

| Feature | Starter | Growth | Enterprise |
|---|---|---|---|
| Users (seats) | 3 | 10 | Unlimited* |
| Contacts | 2 000 | 25 000 | Unlimited |
| Storage | 5 GB | 50 GB | 500 GB |
| API rate limit | 100/min | 1 000/min | 10 000/min |
| SSO | No | Yes | Yes |
| Custom roles | No | No | Yes |
| Priority support | Email | Email + Chat | Dedicated CSM |

*Enterprise: fair-use policy applies beyond 500 active users.

---

## 2. Upgrading

### Self-service upgrade
1. **Admin Console → Billing → Plan → Change Plan**.
2. Select new plan.
3. Prorated charge is calculated immediately.
4. Confirm payment; new limits apply instantly.

### Proration rules
- Upgrades are **prorated by day**.
- The customer is charged the difference between the old and new plan for the remainder of the billing cycle.
- Example: upgrading from Starter (€29/mo) to Growth (€79/mo) on day 15 of 30 = charge ~€25.

### Downgrading restrictions
- Cannot downgrade if current usage exceeds the target plan's limits (e.g. 5 000 contacts on Starter).
- Must reduce usage first or contact Support for a migration plan.

### Enterprise upgrade
- Requires a signed order form or electronic acceptance of Enterprise Terms.
- Annual billing is standard; monthly available with 15% surcharge.
- Implementation and onboarding calls are scheduled separately by the CSM.

---

## 3. Downgrading

### Self-service downgrade
1. **Admin Console → Billing → Plan → Change Plan**.
2. Select lower plan.
3. If checks pass, the change takes effect at the **next billing cycle**.
4. No refund for the current cycle; the account retains higher limits until renewal.

### Post-downgrade behaviour
- Excess contacts are **not deleted** but become read-only.
- New contacts cannot be added until count is within plan limit.
- Excess files are **not deleted**; uploads are blocked until storage is under limit.
- Excess users are **not deactivated**; new invites are blocked. Admin must manually deactivate users.

### Reactivation after downgrade limit hit
1. Reduce contacts/users/storage to within the new plan limit.
2. Read-only restrictions lift automatically within 5 minutes.

---

## 4. Cancellation

### Self-service cancellation
1. **Admin Console → Billing → Plan → Cancel Subscription**.
2. Answer exit survey (optional).
3. Confirm cancellation.
4. Account remains active until the **end of the current billing period**.

### Immediate cancellation (rare)
- Only available for monthly plans within 48 hours of charge.
- Contact `billing@nordlycrm.fi` with reason.
- Data export should be requested **before** cancellation.

### Post-cancellation data retention
- **30 days:** full read/write access (grace period).
- **31–90 days:** read-only access; Admin can reactivate by resubscribing.
- **91+ days:** data enters deletion queue; irreversible.

### Reactivation
1. Admin logs in and clicks **Reactivate**.
2. Chooses plan and payment method.
3. Account restores with all data intact (if within retention window).

---

## 5. Seat Limits

### Seat overage
- Starter and Growth have hard seat caps.
- If an Admin tries to invite beyond the cap:
  > "You have reached the user limit for your plan. Upgrade to add more users."

### Managing seats
- **Deactivate** a user: frees a seat immediately; data is preserved.
- **Delete** a user: frees a seat; associated records can be reassigned or orphaned (Admin choice).
- Re-activating a deactivated user consumes a seat again.

### Enterprise fair-use
- Enterprise includes unlimited seats under fair use.
- Organisations with >500 active users receive a quarterly usage review from their CSM.
- Abnormal seat growth (e.g. 200→2 000 in a week) triggers a Shield review for licence compliance.

---

## 6. Add-ons

| Add-on | Plans | Pricing |
|---|---|---|
| Extra contacts (5 000 pack) | Starter, Growth | €9/mo |
| Extra storage (50 GB pack) | All | €15/mo |
| Advanced API (webhooks, higher limits) | Growth, Enterprise | €29/mo |
| Dedicated IP for email | Enterprise only | €49/mo |

Add-ons can be added/removed mid-cycle and are prorated.

---

## 7. Internal Notes & Escalation

- Do **not** manually override plan limits in the database.
- Do **not** promise custom pricing without Sales/CSM approval.
- Escalate to **Tier 2 / CSM** if:
  - Customer is threatening churn due to pricing.
  - Customer needs a custom contract (multi-year, unusual terms).
  - Seat audit reveals potential licence abuse.
