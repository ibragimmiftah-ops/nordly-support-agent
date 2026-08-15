# Authentication Support Guide — Nordly CRM Oy

**Document owner:** Customer Success Engineering
**Last updated:** 2026-08-13
**Applies to:** All Nordly CRM web, mobile, and API access points

---

## 1. Password Reset

### Self-service reset
1. Go to **https://app.nordlycrm.fi/forgot-password**
2. Enter the registered email address.
3. Click **Send reset link**.
4. Check inbox (and spam/junk) for a message from `noreply@nordlycrm.fi`.
5. Link is valid for **30 minutes** and can be used once.

### Error: "We could not find an account with that email"
- The email may contain a typo.
- The user may have signed up with a different domain (e.g. `first.last@nordly.fi` vs `first.last@nordlycrm.fi`).
- The account may be under a different organisation.
- **Action:** ask the user to verify the exact email from a previous invoice or welcome email.

### Error: "Reset link expired or already used"
- The link timed out or the user clicked it twice.
- **Action:** generate a new request. Advise the user to complete the flow in one browser session without forwarding the email.

### Agent-initiated reset
If the user cannot access their email:
1. Verify identity via organisation Admin or billing contact.
2. In the Admin Console, go to **Users → [Name] → Security → Force password reset**.
3. The user receives a fresh link within 60 seconds.

---

## 2. Account Lock

### Trigger conditions
- **5 consecutive failed password attempts** within 15 minutes.
- **3 consecutive failed MFA codes** within 10 minutes.
- Suspicious behaviour flagged by the Nordly Shield risk engine.

### Error message
> "Your account has been temporarily locked due to too many failed login attempts. Try again in 30 minutes or contact your organisation Admin."

### Unlock procedures
| Scenario | Resolution |
|---|---|
| Standard lock (5 bad passwords) | Auto-unlock after 30 minutes. Admin can unlock immediately. |
| MFA lock (3 bad TOTP codes) | Auto-unlock after 30 minutes. Admin can unlock + force MFA re-enrol if needed. |
| Shield lock (risk signal) | **Requires Admin or Nordly Support review.** Admin sees a "Shield Review" banner on the user card. |

### Admin unlock steps
1. **Admin Console → Users → [Name] → Security → Unlock Account**.
2. Optionally toggle **Require password change on next login**.
3. If Shield flagged the account, add a note before unlocking (audit requirement).

---

## 3. Multi-Factor Authentication (MFA)

### Supported methods
- **TOTP apps:** Google Authenticator, Microsoft Authenticator, Authy, 1Password, Bitwarden.
- **Hardware keys:** FIDO2/WebAuthn (YubiKey, Titan Security Key) on Chrome/Edge/Firefox/Safari.
- **SMS:** available but **discouraged**; requires Admin opt-in per organisation.

### Enrolment
1. User navigates to **Profile → Security → Enable MFA**.
2. Scan QR code with authenticator app.
3. Enter two consecutive TOTP codes to verify sync.
4. Save backup codes (10 single-use codes). Nordly **does not store** backup codes; loss requires Admin reset.

### Error: "Invalid code. Please try again."
- Device clock drift > 30 seconds.
- Wrong MFA method selected (e.g. trying SMS when TOTP is enrolled).
- **Troubleshooting:**
  1. Sync device clock automatically.
  2. Try the next code window (wait 30 seconds).
  3. Use a backup code.

### Lost authenticator / phone
1. User contacts organisation Admin.
2. Admin goes to **Users → [Name] → Security → Reset MFA**.
3. User must re-enrol within 24 hours or the account is suspended.

### MFA enforcement policies
- **Optional** (default)
- **Required for Admins**
- **Required for all users**
- Admin changes apply at next login; users get a 7-day grace period with banner reminders.

---

## 4. Single Sign-On (SSO)

### Supported identity providers
- Microsoft Entra ID (Azure AD)
- Google Workspace
- Okta
- OneLogin
- Generic SAML 2.0
- Generic OpenID Connect (OIDC)

### Setup summary
1. Admin enables SSO in **Admin Console → Security → SSO → Add Provider**.
2. Nordly generates an **ACS URL** and **Entity ID / Audience URI**.
3. Admin configures the IdP and uploads the metadata XML (or pastes OIDC endpoints).
4. Toggle **SSO required** to disable password login for the domain.

### Error: "SAML response invalid"
- Clock skew between IdP and Nordly > 60 seconds.
- Certificate mismatch or expired signing cert.
- Audience URI / Entity ID mismatch.
- **Action:**
  1. Verify IdP clock is NTP-synced.
  2. Re-upload current IdP metadata to Nordly.
  3. Compare Entity ID character-for-character (trailing slashes matter).

### Error: "User not found"
- The SAML NameID or OIDC `email` claim does not match an existing Nordly user.
- **Action:** ensure user provisioning (SCIM) is enabled, or create the user manually with the exact email.

### Just-in-Time (JIT) provisioning
- Enabled by default for SSO.
- First login creates a **Member**-role user.
- Admin must manually promote to Manager or Admin.

### SSO fallback
If the IdP is down, organisation Admins can use a **break-glass** password login once every 24 hours. This is audited and triggers a Shield alert.

---

## 5. Common Login Errors

| Error message | Likely cause | Resolution |
|---|---|---|
| "Invalid email or password" | Typo, caps lock, wrong keyboard layout | Check caps lock, try password manager, reset password |
| "Your session has expired. Please sign in again." | Idle timeout (12h) or absolute timeout (7 days) | Normal; re-authenticate |
| "You do not have access to this organisation." | User removed from org, or invited to wrong org | Admin checks **Users** list; re-invite if needed |
| "Login blocked: unsupported browser" | IE11 or very old Safari | Switch to Chrome, Edge, Firefox, or Safari 14+ |
| "Too many requests. Please slow down." | Rate limit exceeded (10 attempts/min) | Wait 60 seconds; if persistent, check for brute-force scripts |
| "Your account is suspended." | Non-payment, compliance hold, or Admin action | Billing or Support ticket required |

---

## 6. API Authentication

- API keys are scoped to a user and inherit their permissions.
- Keys are visible **once** at creation; lost keys must be revoked and regenerated.
- OAuth 2.0 apps must use the Authorisation Code flow with PKCE.
- Tokens expire in **1 hour**; refresh tokens expire in **30 days**.

### Error: "401 Invalid API key"
- Key revoked or belonging to a deactivated user.
- Key header format: `Authorization: Bearer nk_live_...`

---

## 7. Internal Notes & Escalation

- **Never** send passwords in plaintext via chat or email.
- **Never** disable MFA for a user without Admin approval and identity verification.
- Escalate to **Tier 2** if:
  - Shield lock involves suspected breach (unusual geo-IP, impossible travel).
  - SSO certificate rotation breaks all users.
  - SAML/OIDC debugging requires packet inspection (with customer consent).
