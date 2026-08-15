"""Deterministic guardrails and validation for agent decisions.

All post-processing and safety enforcement happens here, not in the LLM.
"""

from app.agent.schemas import EscalationTeam, ResolutionStatus, SupportCategory, SupportDecision
from app.business_rules import should_auto_escalate

# Actions that the agent must never claim to have performed
PROHIBITED_ACTIONS = {
    "refund",
    "cancel subscription",
    "modify subscription",
    "upgrade plan",
    "downgrade plan",
    "reset password",
    "disable account",
    "enable sso",
    "disable mfa",
    "send email",
    "process payment",
    "issue credit",
    "delete data",
    "approve integration",
}


def validate_and_enforce(
    decision: SupportDecision,
    plan: str | None,
) -> SupportDecision:
    """Validate and enforce business rules on an agent decision.

    Args:
        decision: Raw decision from the agent.
        plan: Customer plan type string or None.

    Returns:
        Validated and potentially modified decision.
    """
    # Auto-escalate security categories
    if decision.category == SupportCategory.SECURITY:
        decision.escalation_required = True
        decision.escalation_team = EscalationTeam.SECURITY
        decision.escalation_reason = (
            decision.escalation_reason or "Auto-escalated: security-related ticket"
        )
        decision.resolution_status = ResolutionStatus.ESCALATED

    # Auto-escalate based on category rules
    auto_team = should_auto_escalate(decision.category.value)
    if auto_team and not decision.escalation_required:
        decision.escalation_required = True
        decision.escalation_team = auto_team
        decision.escalation_reason = f"Auto-escalated: {decision.category.value} category"
        decision.resolution_status = ResolutionStatus.ESCALATED

    # Escalate very low confidence
    if decision.confidence < 0.5 and decision.resolution_status not in (
        ResolutionStatus.ESCALATED,
        ResolutionStatus.NEEDS_CUSTOMER_INFORMATION,
    ):
        decision.escalation_required = True
        decision.escalation_team = decision.escalation_team or EscalationTeam.SENIOR_SUPPORT
        decision.escalation_reason = (
            decision.escalation_reason or f"Confidence too low ({decision.confidence:.2f})"
        )
        decision.resolution_status = ResolutionStatus.ESCALATED

    # Ensure escalation fields are consistent
    if decision.escalation_required:
        decision.resolution_status = ResolutionStatus.ESCALATED
        if not decision.escalation_team:
            decision.escalation_team = EscalationTeam.SENIOR_SUPPORT
        if not decision.escalation_reason:
            decision.escalation_reason = "Escalated by system guardrails"
    else:
        decision.escalation_team = None
        decision.escalation_reason = None

    # Ensure reply_draft exists for resolved/reply_ready
    if (
        decision.resolution_status
        in (
            ResolutionStatus.RESOLVED,
            ResolutionStatus.REPLY_READY,
        )
        and not decision.reply_draft
    ):
        decision.reply_draft = (
            "Thank you for contacting Nordly Support. We are reviewing your request."
        )

    return decision


def check_prohibited_actions(decision: SupportDecision) -> list[str]:
    """Check if the decision contains claims of prohibited actions.

    Args:
        decision: Agent decision to check.

    Returns:
        List of detected prohibited action claims.
    """
    violations: list[str] = []
    text_to_check = " ".join(
        filter(
            None,
            [
                decision.reply_draft,
                decision.investigation_summary,
                decision.recommended_internal_action,
            ],
        )
    ).lower()

    for action in PROHIBITED_ACTIONS:
        if action in text_to_check:
            violations.append(action)

    return violations
