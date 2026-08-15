"""Idempotent database seeding for Nordly demo data."""

import hashlib
import json
from datetime import datetime, timedelta

from app.database import get_connection, init_database

SEED_NOW = datetime(2026, 1, 15, 12, 0, 0)

CUSTOMERS = [
    {
        "customer_id": "C-NL-1001",
        "company": "Bergen Logistics AS",
        "domain": "bergenlogistics.no",
        "account_state": "active",
        "country": "Norway",
        "seats": 25,
        "plan": "Pro",
        "main_contact_email": "support@bergenlogistics.no",
    },
    {
        "customer_id": "C-NL-1002",
        "company": "Helsinki Design Oy",
        "domain": "helsinkidesign.fi",
        "account_state": "active",
        "country": "Finland",
        "seats": 8,
        "plan": "Starter",
        "main_contact_email": "admin@helsinkidesign.fi",
    },
    {
        "customer_id": "C-NL-1003",
        "company": "Copenhagen Retail A/S",
        "domain": "cphretail.dk",
        "account_state": "billing_hold",
        "country": "Denmark",
        "seats": 45,
        "plan": "Business",
        "main_contact_email": "it@cphretail.dk",
    },
    {
        "customer_id": "C-NL-1004",
        "company": "Stockholm Tech AB",
        "domain": "stockholmtech.se",
        "account_state": "active",
        "country": "Sweden",
        "seats": 120,
        "plan": "Business",
        "main_contact_email": "helpdesk@stockholmtech.se",
    },
    {
        "customer_id": "C-NL-1005",
        "company": "Tallinn Software OÜ",
        "domain": "tallinnsoft.ee",
        "account_state": "trial",
        "country": "Estonia",
        "seats": 5,
        "plan": "Pro",
        "main_contact_email": "info@tallinnsoft.ee",
    },
    {
        "customer_id": "C-NL-1006",
        "company": "Riga Consulting SIA",
        "domain": "rigaconsulting.lv",
        "account_state": "active",
        "country": "Latvia",
        "seats": 15,
        "plan": "Pro",
        "main_contact_email": "support@rigaconsulting.lv",
    },
    {
        "customer_id": "C-NL-1007",
        "company": "Vilnius Manufacturing UAB",
        "domain": "vilniusmfg.lt",
        "account_state": "suspended",
        "country": "Lithuania",
        "seats": 30,
        "plan": "Business",
        "main_contact_email": "admin@vilniusmfg.lt",
    },
    {
        "customer_id": "C-NL-1008",
        "company": "Oslo Finance AS",
        "domain": "oslofinance.no",
        "account_state": "active",
        "country": "Norway",
        "seats": 60,
        "plan": "Business",
        "main_contact_email": "security@oslofinance.no",
    },
    {
        "customer_id": "C-NL-1009",
        "company": "Reykjavik Services ehf",
        "domain": "reykservices.is",
        "account_state": "active",
        "country": "Iceland",
        "seats": 12,
        "plan": "Starter",
        "main_contact_email": "contact@reykservices.is",
    },
    {
        "customer_id": "C-NL-1010",
        "company": "Berlin Nord GmbH",
        "domain": "berlinnord.de",
        "account_state": "cancelled",
        "country": "Germany",
        "seats": 3,
        "plan": "Starter",
        "main_contact_email": "admin@berlinnord.de",
    },
    {
        "customer_id": "C-NL-1011",
        "company": "Amsterdam Trade BV",
        "domain": "amstrade.nl",
        "account_state": "active",
        "country": "Netherlands",
        "seats": 35,
        "plan": "Pro",
        "main_contact_email": "support@amstrade.nl",
    },
    {
        "customer_id": "C-NL-1012",
        "company": "Warsaw Digital Sp. z o.o.",
        "domain": "warsawdigital.pl",
        "account_state": "active",
        "country": "Poland",
        "seats": 50,
        "plan": "Business",
        "main_contact_email": "help@warsawdigital.pl",
    },
    {
        "customer_id": "C-NL-1013",
        "company": "Prague Solutions s.r.o.",
        "domain": "praguesolutions.cz",
        "account_state": "security_lock",
        "country": "Czech Republic",
        "seats": 20,
        "plan": "Pro",
        "main_contact_email": "admin@praguesolutions.cz",
    },
    {
        "customer_id": "C-NL-1014",
        "company": "Vienna Consulting GmbH",
        "domain": "viennaconsult.at",
        "account_state": "active",
        "country": "Austria",
        "seats": 18,
        "plan": "Pro",
        "main_contact_email": "support@viennaconsult.at",
    },
    {
        "customer_id": "C-NL-1015",
        "company": "Dublin SaaS Ltd",
        "domain": "dublinsaas.ie",
        "account_state": "trial",
        "country": "Ireland",
        "seats": 6,
        "plan": "Starter",
        "main_contact_email": "info@dublinsaas.ie",
    },
    {
        "customer_id": "C-NL-1016",
        "company": "Lisbon Metrics Lda",
        "domain": "lisbonmetrics.pt",
        "account_state": "active",
        "country": "Portugal",
        "seats": 22,
        "plan": "Pro",
        "main_contact_email": "ops@lisbonmetrics.pt",
    },
    {
        "customer_id": "C-NL-1017",
        "company": "Madrid Fieldworks SL",
        "domain": "madridfieldworks.es",
        "account_state": "active",
        "country": "Spain",
        "seats": 9,
        "plan": "Starter",
        "main_contact_email": "admin@madridfieldworks.es",
    },
    {
        "customer_id": "C-NL-1018",
        "company": "Paris Atelier SAS",
        "domain": "parisatelier.fr",
        "account_state": "active",
        "country": "France",
        "seats": 42,
        "plan": "Pro",
        "main_contact_email": "crm@parisatelier.fr",
    },
    {
        "customer_id": "C-NL-1019",
        "company": "Brussels Mobility NV",
        "domain": "brusselsmobility.be",
        "account_state": "billing_hold",
        "country": "Belgium",
        "seats": 75,
        "plan": "Business",
        "main_contact_email": "finance@brusselsmobility.be",
    },
    {
        "customer_id": "C-NL-1020",
        "company": "Luxembourg Ledger SARL",
        "domain": "luxledger.lu",
        "account_state": "active",
        "country": "Luxembourg",
        "seats": 28,
        "plan": "Pro",
        "main_contact_email": "security@luxledger.lu",
    },
    {
        "customer_id": "C-NL-1021",
        "company": "Rome Commerce SRL",
        "domain": "romecommerce.it",
        "account_state": "active",
        "country": "Italy",
        "seats": 110,
        "plan": "Business",
        "main_contact_email": "support@romecommerce.it",
    },
    {
        "customer_id": "C-NL-1022",
        "company": "Athens Marine PC",
        "domain": "athensmarine.gr",
        "account_state": "trial",
        "country": "Greece",
        "seats": 7,
        "plan": "Starter",
        "main_contact_email": "hello@athensmarine.gr",
    },
    {
        "customer_id": "C-NL-1023",
        "company": "Zagreb Systems d.o.o.",
        "domain": "zagrebsystems.hr",
        "account_state": "active",
        "country": "Croatia",
        "seats": 34,
        "plan": "Pro",
        "main_contact_email": "it@zagrebsystems.hr",
    },
    {
        "customer_id": "C-NL-1024",
        "company": "Ljubljana Labs d.o.o.",
        "domain": "ljubljanalabs.si",
        "account_state": "security_lock",
        "country": "Slovenia",
        "seats": 16,
        "plan": "Pro",
        "main_contact_email": "admin@ljubljanalabs.si",
    },
    {
        "customer_id": "C-NL-1025",
        "company": "Bucharest Data SRL",
        "domain": "bucharestdata.ro",
        "account_state": "active",
        "country": "Romania",
        "seats": 85,
        "plan": "Business",
        "main_contact_email": "help@bucharestdata.ro",
    },
]

PLAN_FEATURES = {
    "Starter": ["contact_management", "deals", "tasks", "email_integration", "basic_reporting"],
    "Pro": [
        "contact_management",
        "deals",
        "tasks",
        "email_integration",
        "basic_reporting",
        "automations",
        "advanced_reporting",
        "api_access",
        "integrations",
        "team_permissions",
    ],
    "Business": [
        "contact_management",
        "deals",
        "tasks",
        "email_integration",
        "basic_reporting",
        "automations",
        "advanced_reporting",
        "api_access",
        "integrations",
        "team_permissions",
        "advanced_permissions",
        "sso",
        "audit_logs",
        "custom_integrations",
        "priority_support",
        "onboarding_assistance",
    ],
}

PLAN_PRICES = {"Starter": 39.0, "Pro": 99.0, "Business": 299.0}
PLAN_SEATS = {"Starter": 10, "Pro": 50, "Business": 200}

ACCOUNT_STATUSES = {
    "C-NL-1001": {"state": "active", "mfa_enabled": True, "sso_enabled": False},
    "C-NL-1002": {"state": "active", "mfa_enabled": False, "sso_enabled": False},
    "C-NL-1003": {
        "state": "billing_hold",
        "state_reason": "Overdue invoice #INV-2041-0892 for 3 months",
        "mfa_enabled": True,
        "sso_enabled": True,
    },
    "C-NL-1004": {"state": "active", "mfa_enabled": True, "sso_enabled": True},
    "C-NL-1005": {"state": "trial", "mfa_enabled": False, "sso_enabled": False},
    "C-NL-1006": {"state": "active", "mfa_enabled": True, "sso_enabled": False},
    "C-NL-1007": {
        "state": "suspended",
        "state_reason": "Violation of terms of service - data scraping detected",
        "mfa_enabled": False,
        "sso_enabled": False,
        "suspicious_activity": True,
    },
    "C-NL-1008": {"state": "active", "mfa_enabled": True, "sso_enabled": True},
    "C-NL-1009": {"state": "active", "mfa_enabled": False, "sso_enabled": False},
    "C-NL-1010": {"state": "cancelled", "state_reason": "Churned - moved to competitor"},
    "C-NL-1011": {"state": "active", "mfa_enabled": True, "sso_enabled": False},
    "C-NL-1012": {"state": "active", "mfa_enabled": True, "sso_enabled": True},
    "C-NL-1013": {
        "state": "security_lock",
        "state_reason": "Suspicious login attempts from multiple countries",
        "mfa_enabled": True,
        "sso_enabled": True,
        "suspicious_activity": True,
    },
    "C-NL-1014": {"state": "active", "mfa_enabled": True, "sso_enabled": False},
    "C-NL-1015": {"state": "trial", "mfa_enabled": False, "sso_enabled": False},
    "C-NL-1016": {"state": "active", "mfa_enabled": True, "sso_enabled": False},
    "C-NL-1017": {"state": "active", "mfa_enabled": False, "sso_enabled": False},
    "C-NL-1018": {"state": "active", "mfa_enabled": True, "sso_enabled": False},
    "C-NL-1019": {
        "state": "billing_hold",
        "state_reason": "Payment method expired",
        "mfa_enabled": True,
        "sso_enabled": True,
    },
    "C-NL-1020": {"state": "active", "mfa_enabled": True, "sso_enabled": False},
    "C-NL-1021": {"state": "active", "mfa_enabled": True, "sso_enabled": True},
    "C-NL-1022": {"state": "trial", "mfa_enabled": False, "sso_enabled": False},
    "C-NL-1023": {"state": "active", "mfa_enabled": True, "sso_enabled": False},
    "C-NL-1024": {
        "state": "security_lock",
        "state_reason": "Compromised administrator credentials",
        "mfa_enabled": True,
        "sso_enabled": False,
        "suspicious_activity": True,
    },
    "C-NL-1025": {"state": "active", "mfa_enabled": True, "sso_enabled": True},
}
INCIDENTS = [
    {
        "incident_id": "INC-2041",
        "title": "Authentication service degradation",
        "product_area": "authentication",
        "status": "investigating",
        "severity": "critical",
        "description": (
            "Users experiencing intermittent login failures across all regions. SSO and MFA "
            "flows affected. Engineering team investigating root cause."
        ),
        "started_at": (SEED_NOW - timedelta(hours=2)).isoformat(),
        "resolved_at": None,
        "affected_customers": [],
    },
    {
        "incident_id": "INC-2040",
        "title": "Gmail integration sync delays",
        "product_area": "integrations",
        "status": "identified",
        "severity": "minor",
        "description": (
            "Gmail email sync experiencing 15-30 minute delays. Outlook and other integrations "
            "unaffected."
        ),
        "started_at": (SEED_NOW - timedelta(hours=6)).isoformat(),
        "resolved_at": None,
        "affected_customers": ["C-NL-1001", "C-NL-1011"],
    },
    {
        "incident_id": "INC-2039",
        "title": "CSV import processing errors",
        "product_area": "data_import_export",
        "status": "monitoring",
        "severity": "major",
        "description": (
            "Large CSV imports (>10k rows) failing with encoding errors. Workaround: split into "
            "smaller files. Fix deployed, monitoring stability."
        ),
        "started_at": (SEED_NOW - timedelta(days=1)).isoformat(),
        "resolved_at": None,
        "affected_customers": ["C-NL-1004", "C-NL-1012"],
    },
    {
        "incident_id": "INC-2038",
        "title": "API rate limiting issues",
        "product_area": "api",
        "status": "resolved",
        "severity": "major",
        "description": (
            "API rate limits incorrectly applied to Business plan customers. Issue resolved, "
            "monitoring continues."
        ),
        "started_at": (SEED_NOW - timedelta(days=3)).isoformat(),
        "resolved_at": (SEED_NOW - timedelta(days=2)).isoformat(),
        "affected_customers": ["C-NL-1004", "C-NL-1008"],
    },
    {
        "incident_id": "INC-2037",
        "title": "Billing calculation error for annual subscriptions",
        "product_area": "billing",
        "status": "resolved",
        "severity": "minor",
        "description": (
            "Annual subscription renewals showing incorrect prorated amounts. Fixed and refunds "
            "processed."
        ),
        "started_at": (SEED_NOW - timedelta(days=5)).isoformat(),
        "resolved_at": (SEED_NOW - timedelta(days=4)).isoformat(),
        "affected_customers": ["C-NL-1003"],
    },
    {
        "incident_id": "INC-2036",
        "title": "Slack integration webhook failures",
        "product_area": "integrations",
        "status": "resolved",
        "severity": "minor",
        "description": (
            "Slack notifications failing due to expired webhook certificates. Certificates "
            "renewed and integrations restored."
        ),
        "started_at": (SEED_NOW - timedelta(days=7)).isoformat(),
        "resolved_at": (SEED_NOW - timedelta(days=6)).isoformat(),
        "affected_customers": ["C-NL-1012"],
    },
    {
        "incident_id": "INC-2035",
        "title": "Database backup delays",
        "product_area": "infrastructure",
        "status": "resolved",
        "severity": "major",
        "description": (
            "Automated backups running 4 hours behind schedule. No data loss. Backlog cleared "
            "and schedule restored."
        ),
        "started_at": (SEED_NOW - timedelta(days=10)).isoformat(),
        "resolved_at": (SEED_NOW - timedelta(days=9)).isoformat(),
        "affected_customers": [],
    },
]

HISTORICAL_TICKETS = [
    {
        "customer_email": "support@bergenlogistics.no",
        "subject": "How to set up MFA for my team",
        "message": "We want to enable two-factor authentication for all users. What are the steps?",
        "product_area": "authentication",
        "status": "resolved",
        "priority": "P3",
        "category": "authentication",
    },
    {
        "customer_email": "admin@helsinkidesign.fi",
        "subject": "Can I upgrade from Starter to Pro?",
        "message": "We are growing and need more seats and API access. What is the process?",
        "product_area": "subscription",
        "status": "resolved",
        "priority": "P3",
        "category": "subscription",
    },
    {
        "customer_email": "it@cphretail.dk",
        "subject": "Invoice discrepancy - charged twice",
        "message": "Our last invoice shows double the expected amount. Please investigate.",
        "product_area": "billing",
        "status": "escalated",
        "priority": "P2",
        "category": "billing",
    },
    {
        "customer_email": "helpdesk@stockholmtech.se",
        "subject": "API returning 429 errors",
        "message": "Our integrations are failing due to rate limiting. We are on Business plan.",
        "product_area": "api",
        "status": "resolved",
        "priority": "P1",
        "category": "bug",
    },
    {
        "customer_email": "info@tallinnsoft.ee",
        "subject": "Trial extension request",
        "message": "We need 2 more weeks to evaluate the platform. Is this possible?",
        "product_area": "subscription",
        "status": "resolved",
        "priority": "P4",
        "category": "subscription",
    },
    {
        "customer_email": "support@rigaconsulting.lv",
        "subject": "Gmail sync not working",
        "message": "Emails are not syncing since yesterday. We have tried reconnecting.",
        "product_area": "integrations",
        "status": "resolved",
        "priority": "P2",
        "category": "integrations",
    },
    {
        "customer_email": "admin@vilniusmfg.lt",
        "subject": "Account suspended - why?",
        "message": "Our account was suspended without warning. We need immediate access restored.",
        "product_area": "account",
        "status": "escalated",
        "priority": "P1",
        "category": "account",
    },
    {
        "customer_email": "security@oslofinance.no",
        "subject": "Suspicious login from unknown IP",
        "message": "We detected a login from an unusual location. Please investigate immediately.",
        "product_area": "security",
        "status": "escalated",
        "priority": "P1",
        "category": "security",
    },
    {
        "customer_email": "contact@reykservices.is",
        "subject": "How to export contacts to CSV",
        "message": "We need to export all contacts for a backup. What is the procedure?",
        "product_area": "data_import_export",
        "status": "resolved",
        "priority": "P4",
        "category": "feature_question",
    },
    {
        "customer_email": "admin@berlinnord.de",
        "subject": "Cancel subscription",
        "message": "Please cancel our subscription effective immediately.",
        "product_area": "subscription",
        "status": "resolved",
        "priority": "P3",
        "category": "subscription",
    },
    {
        "customer_email": "support@amstrade.nl",
        "subject": "Outlook calendar sync issues",
        "message": "Calendar events are not syncing bidirectionally with Outlook.",
        "product_area": "integrations",
        "status": "resolved",
        "priority": "P3",
        "category": "integrations",
    },
    {
        "customer_email": "help@warsawdigital.pl",
        "subject": "CSV import fails with UTF-8 error",
        "message": "Importing a CSV with Polish characters fails. We have checked the encoding.",
        "product_area": "data_import_export",
        "status": "resolved",
        "priority": "P2",
        "category": "bug",
    },
    {
        "customer_email": "admin@praguesolutions.cz",
        "subject": "Account locked after failed logins",
        "message": "Our admin account is locked. We need it unlocked urgently.",
        "product_area": "authentication",
        "status": "escalated",
        "priority": "P2",
        "category": "authentication",
    },
    {
        "customer_email": "support@viennaconsult.at",
        "subject": "Zapier integration setup help",
        "message": "We are trying to connect Nordly to Zapier but the trigger is not firing.",
        "product_area": "integrations",
        "status": "resolved",
        "priority": "P3",
        "category": "integrations",
    },
    {
        "customer_email": "info@dublinsaas.ie",
        "subject": "Feature request: custom dashboards",
        "message": "We would like to build custom dashboards for our clients.",
        "product_area": "feature_question",
        "status": "resolved",
        "priority": "P4",
        "category": "feature_question",
    },
    {
        "customer_email": "support@bergenlogistics.no",
        "subject": "SSO configuration with Azure AD",
        "message": "We need help configuring SSO with Microsoft Azure AD.",
        "product_area": "authentication",
        "status": "resolved",
        "priority": "P2",
        "category": "authentication",
    },
    {
        "customer_email": "helpdesk@stockholmtech.se",
        "subject": "Seat limit reached",
        "message": "We cannot add new users. It says we have reached the limit.",
        "product_area": "subscription",
        "status": "resolved",
        "priority": "P3",
        "category": "subscription",
    },
    {
        "customer_email": "it@cphretail.dk",
        "subject": "Refund for duplicate charge",
        "message": "We were charged twice for the same invoice. Please process a refund.",
        "product_area": "billing",
        "status": "escalated",
        "priority": "P2",
        "category": "billing",
    },
    {
        "customer_email": "admin@helsinkidesign.fi",
        "subject": "Cannot access reports",
        "message": "The reporting page shows an error when we try to generate quarterly reports.",
        "product_area": "performance",
        "status": "resolved",
        "priority": "P3",
        "category": "bug",
    },
    {
        "customer_email": "security@oslofinance.no",
        "subject": "Data export compliance question",
        "message": "We need to export all data for GDPR compliance. What is the process?",
        "product_area": "data_import_export",
        "status": "resolved",
        "priority": "P2",
        "category": "feature_question",
    },
    {
        "customer_email": "ops@lisbonmetrics.pt",
        "subject": "Automation skipped new leads",
        "message": "Our lead assignment automation skipped several records this morning.",
        "product_area": "automations",
        "status": "resolved",
        "priority": "P2",
        "category": "bug",
    },
    {
        "customer_email": "admin@madridfieldworks.es",
        "subject": "Import contacts from spreadsheet",
        "message": "How can we map custom columns while importing our contact spreadsheet?",
        "product_area": "data_import_export",
        "status": "resolved",
        "priority": "P4",
        "category": "feature_question",
    },
    {
        "customer_email": "crm@parisatelier.fr",
        "subject": "Email template formatting",
        "message": "Saved email templates lose list formatting when sent.",
        "product_area": "email",
        "status": "resolved",
        "priority": "P3",
        "category": "bug",
    },
    {
        "customer_email": "finance@brusselsmobility.be",
        "subject": "Account unavailable after failed payment",
        "message": "Our payment method was updated but users still cannot access Nordly.",
        "product_area": "billing",
        "status": "escalated",
        "priority": "P2",
        "category": "billing",
    },
    {
        "customer_email": "security@luxledger.lu",
        "subject": "Audit log retention",
        "message": "Please confirm how long security audit logs remain available.",
        "product_area": "security",
        "status": "resolved",
        "priority": "P3",
        "category": "security",
    },
    {
        "customer_email": "support@romecommerce.it",
        "subject": "SSO certificate rotation",
        "message": "Our identity provider certificate expires next month and needs rotation.",
        "product_area": "authentication",
        "status": "resolved",
        "priority": "P2",
        "category": "authentication",
    },
    {
        "customer_email": "hello@athensmarine.gr",
        "subject": "Invite trial teammates",
        "message": "Can all seven colleagues join during our trial period?",
        "product_area": "subscription",
        "status": "resolved",
        "priority": "P4",
        "category": "subscription",
    },
    {
        "customer_email": "it@zagrebsystems.hr",
        "subject": "Webhook deliveries delayed",
        "message": "Deal update webhooks arrive about twenty minutes late.",
        "product_area": "api",
        "status": "resolved",
        "priority": "P2",
        "category": "integrations",
    },
    {
        "customer_email": "admin@ljubljanalabs.si",
        "subject": "Administrator account compromised",
        "message": "An unknown user changed our administrator profile. Lock all access now.",
        "product_area": "security",
        "status": "escalated",
        "priority": "P1",
        "category": "security",
    },
    {
        "customer_email": "help@bucharestdata.ro",
        "subject": "Custom report totals differ",
        "message": "Pipeline totals in our custom report differ from the deal list.",
        "product_area": "reporting",
        "status": "resolved",
        "priority": "P3",
        "category": "bug",
    },
    {
        "customer_email": "ops@lisbonmetrics.pt",
        "subject": "Connect Microsoft Teams",
        "message": "We need guidance connecting deal alerts to Microsoft Teams.",
        "product_area": "integrations",
        "status": "resolved",
        "priority": "P3",
        "category": "integrations",
    },
    {
        "customer_email": "crm@parisatelier.fr",
        "subject": "Bulk merge duplicate contacts",
        "message": "Can we merge several hundred duplicate contacts in bulk?",
        "product_area": "contacts",
        "status": "resolved",
        "priority": "P3",
        "category": "feature_question",
    },
    {
        "customer_email": "support@romecommerce.it",
        "subject": "API pagination question",
        "message": "How should our integration follow cursors when listing deals?",
        "product_area": "api",
        "status": "resolved",
        "priority": "P4",
        "category": "feature_question",
    },
    {
        "customer_email": "it@zagrebsystems.hr",
        "subject": "Permission group cannot edit deals",
        "message": "A custom permission group unexpectedly lost deal editing access.",
        "product_area": "permissions",
        "status": "resolved",
        "priority": "P2",
        "category": "bug",
    },
    {
        "customer_email": "help@bucharestdata.ro",
        "subject": "Onboarding workshop scheduling",
        "message": "We would like to schedule the onboarding workshop included in Business.",
        "product_area": "onboarding",
        "status": "resolved",
        "priority": "P3",
        "category": "feature_question",
    },
]


def seed_customers():
    """Seed customer records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for customer in CUSTOMERS:
            cursor.execute(
                """INSERT OR IGNORE INTO customers
                   (customer_id, company, domain, account_state, country, seats, plan,
                    main_contact_email)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    customer["customer_id"],
                    customer["company"],
                    customer["domain"],
                    customer["account_state"],
                    customer["country"],
                    customer["seats"],
                    customer["plan"],
                    customer["main_contact_email"],
                ),
            )
        conn.commit()


def seed_subscriptions():
    """Seed subscription records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for index, customer in enumerate(CUSTOMERS):
            plan = customer["plan"]
            renewal = (SEED_NOW + timedelta(days=30 + index * 11)).strftime("%Y-%m-%d")
            features = PLAN_FEATURES[plan]
            price = PLAN_PRICES[plan]
            seat_limit = PLAN_SEATS[plan]
            billing = "active"
            if customer["account_state"] == "trial":
                billing = "trial"
            elif customer["account_state"] == "billing_hold":
                billing = "overdue"
            elif customer["account_state"] == "cancelled":
                billing = "cancelled"

            cursor.execute(
                """INSERT OR IGNORE INTO subscriptions
                   (customer_id, plan, billing_status, renewal_date, cancellation_status,
                    seat_limit, features, monthly_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    customer["customer_id"],
                    plan,
                    billing,
                    renewal,
                    False,
                    seat_limit,
                    json.dumps(features),
                    price,
                ),
            )
        conn.commit()


def seed_account_statuses():
    """Seed account status records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for index, customer in enumerate(CUSTOMERS):
            cid = customer["customer_id"]
            status = ACCOUNT_STATUSES.get(cid, {})
            last_login = (SEED_NOW - timedelta(days=index % 31)).strftime("%Y-%m-%d")
            cursor.execute(
                """INSERT OR IGNORE INTO account_status
                   (customer_id, state, state_reason, last_login, mfa_enabled, sso_enabled,
                    suspicious_activity, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cid,
                    status.get("state", customer["account_state"]),
                    status.get("state_reason"),
                    last_login,
                    status.get("mfa_enabled", False),
                    status.get("sso_enabled", False),
                    status.get("suspicious_activity", False),
                    status.get("notes"),
                ),
            )
        conn.commit()


def seed_incidents():
    """Seed incident records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for incident in INCIDENTS:
            cursor.execute(
                """INSERT OR IGNORE INTO incidents
                   (incident_id, title, product_area, status, severity, description,
                    started_at, resolved_at, affected_customers)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    incident["incident_id"],
                    incident["title"],
                    incident["product_area"],
                    incident["status"],
                    incident["severity"],
                    incident["description"],
                    incident["started_at"],
                    incident["resolved_at"],
                    json.dumps(incident["affected_customers"]),
                ),
            )
        conn.commit()


def seed_historical_tickets():
    """Seed historical tickets."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for index, ticket in enumerate(HISTORICAL_TICKETS):
            identity = f"{ticket['customer_email']}\0{ticket['subject']}".encode()
            ticket_id = f"TICK-{hashlib.sha256(identity).hexdigest()[:12].upper()}"
            created = (SEED_NOW - timedelta(days=index + 1)).isoformat()
            cursor.execute(
                """INSERT OR IGNORE INTO tickets
                   (ticket_id, customer_email, subject, message, product_area, status,
                    priority, category, created_at, analyzed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ticket_id,
                    ticket["customer_email"],
                    ticket["subject"],
                    ticket["message"],
                    ticket["product_area"],
                    ticket["status"],
                    ticket["priority"],
                    ticket["category"],
                    created,
                    created,
                ),
            )
        conn.commit()


def seed_all():
    """Run all seeding operations idempotently."""
    print("Initializing database...")
    init_database()
    print("Seeding customers...")
    seed_customers()
    print("Seeding subscriptions...")
    seed_subscriptions()
    print("Seeding account statuses...")
    seed_account_statuses()
    print("Seeding incidents...")
    seed_incidents()
    print("Seeding historical tickets...")
    seed_historical_tickets()
    print("Seeding complete.")


if __name__ == "__main__":
    seed_all()
