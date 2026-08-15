"""Deterministic business rules for Nordly Support Agent.

This module contains all canonical business logic that must NOT be
invented by the LLM. The agent can classify priority; Python calculates
SLA, escalation rules, and plan features deterministically.
"""

from app.agent.schemas import EscalationTeam, PlanType, Priority

# Plan pricing and features
PLAN_CONFIG = {
    PlanType.STARTER: {
        "monthly_price_eur": 39.0,
        "seat_limit": 10,
        "features": [
            "contact_management",
            "deals",
            "tasks",
            "email_integration",
            "basic_reporting",
        ],
    },
    PlanType.PRO: {
        "monthly_price_eur": 99.0,
        "seat_limit": 50,
        "features": [
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
    },
    PlanType.BUSINESS: {
        "monthly_price_eur": 299.0,
        "seat_limit": 200,
        "features": [
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
    },
}

# SLA matrix in minutes: plan -> priority -> minutes
SLA_MATRIX = {
    PlanType.BUSINESS: {
        Priority.P1_CRITICAL: 30,
        Priority.P2_HIGH: 120,
        Priority.P3_NORMAL: 480,
        Priority.P4_LOW: 480,
    },
    PlanType.PRO: {
        Priority.P1_CRITICAL: 60,
        Priority.P2_HIGH: 240,
        Priority.P3_NORMAL: 720,
        Priority.P4_LOW: 720,
    },
    PlanType.STARTER: {
        Priority.P1_CRITICAL: 240,
        Priority.P2_HIGH: 480,
        Priority.P3_NORMAL: 1440,
        Priority.P4_LOW: 1440,
    },
}

# Escalation triggers by category
AUTO_ESCALATE_CATEGORIES = {
    "security": EscalationTeam.SECURITY,
}


def calculate_sla_minutes(plan: PlanType, priority: Priority) -> int:
    """Calculate SLA in minutes based on plan and priority.

    This is deterministic business logic. The LLM suggests priority;
    Python computes the actual SLA.

    Args:
        plan: Customer subscription plan
        priority: Assigned priority level

    Returns:
        SLA in minutes
    """
    return SLA_MATRIX[plan][priority]


def get_plan_features(plan: PlanType) -> list[str]:
    """Return the list of features available for a plan."""
    return PLAN_CONFIG[plan]["features"]


def get_plan_price(plan: PlanType) -> float:
    """Return the monthly price for a plan."""
    return PLAN_CONFIG[plan]["monthly_price_eur"]


def get_plan_seat_limit(plan: PlanType) -> int:
    """Return the seat limit for a plan."""
    return PLAN_CONFIG[plan]["seat_limit"]


def should_auto_escalate(category: str) -> EscalationTeam | None:
    """Determine if a category requires automatic escalation.

    Args:
        category: Support category string

    Returns:
        EscalationTeam if auto-escalation required, None otherwise
    """
    return AUTO_ESCALATE_CATEGORIES.get(category)
