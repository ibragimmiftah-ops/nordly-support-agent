"""Pydantic schemas and enums for the Nordly Support Agent."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class SupportCategory(StrEnum):
    """Support ticket categories."""

    AUTHENTICATION = "authentication"
    ACCOUNT = "account"
    BILLING = "billing"
    SUBSCRIPTION = "subscription"
    INTEGRATIONS = "integrations"
    DATA_IMPORT_EXPORT = "data_import_export"
    PERMISSIONS = "permissions"
    PERFORMANCE = "performance"
    OUTAGE = "outage"
    SECURITY = "security"
    FEATURE_QUESTION = "feature_question"
    BUG = "bug"
    OTHER = "other"


class Priority(StrEnum):
    """Support ticket priority levels."""

    P1_CRITICAL = "P1"
    P2_HIGH = "P2"
    P3_NORMAL = "P3"
    P4_LOW = "P4"


class Sentiment(StrEnum):
    """Customer sentiment of the ticket."""

    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class ResolutionStatus(StrEnum):
    """Agent resolution decision status."""

    RESOLVED = "resolved"
    REPLY_READY = "reply_ready"
    NEEDS_CUSTOMER_INFORMATION = "needs_customer_information"
    ESCALATED = "escalated"


class EscalationTeam(StrEnum):
    """Teams to which cases can be escalated."""

    SECURITY = "security"
    ENGINEERING = "engineering"
    BILLING = "billing"
    SENIOR_SUPPORT = "senior_support"


class AccountState(StrEnum):
    """Account status states."""

    ACTIVE = "active"
    TRIAL = "trial"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    BILLING_HOLD = "billing_hold"
    SECURITY_LOCK = "security_lock"


class BillingStatus(StrEnum):
    """Billing status for subscriptions."""

    ACTIVE = "active"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    TRIAL = "trial"
    PENDING_CANCELLATION = "pending_cancellation"


class PlanType(StrEnum):
    """Nordly subscription plans."""

    STARTER = "Starter"
    PRO = "Pro"
    BUSINESS = "Business"


class SupportTicketRequest(BaseModel):
    """Incoming support ticket request."""

    customer_email: EmailStr = Field(..., description="Customer email address")
    subject: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Ticket subject line",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Ticket message body",
    )
    product_area: str | None = Field(
        default=None,
        max_length=200,
        description="Optional product area (e.g., authentication, billing)",
    )

    @field_validator("subject", "message")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading and trailing whitespace from text fields."""
        return v.strip()


class Customer(BaseModel):
    """Nordly customer record."""

    customer_id: str = Field(..., description="Unique customer identifier")
    company: str = Field(..., description="Company name")
    domain: str = Field(..., description="Company email domain")
    account_state: AccountState = Field(..., description="Current account state")
    country: str = Field(..., description="Country of operation")
    seats: int = Field(..., ge=1, description="Number of licensed seats")
    plan: PlanType = Field(..., description="Current subscription plan")
    main_contact_email: EmailStr = Field(..., description="Primary contact email")
    created_at: datetime | None = Field(default=None)


class Subscription(BaseModel):
    """Customer subscription details."""

    customer_id: str = Field(..., description="Associated customer ID")
    plan: PlanType = Field(..., description="Subscription plan")
    billing_status: BillingStatus = Field(..., description="Current billing status")
    renewal_date: str | None = Field(default=None, description="Next renewal date (YYYY-MM-DD)")
    cancellation_status: bool = Field(default=False, description="Whether cancellation is pending")
    seat_limit: int = Field(..., ge=1, description="Maximum allowed seats")
    features: list[str] = Field(default_factory=list, description="Enabled features")
    monthly_price: float = Field(..., ge=0, description="Monthly subscription price in EUR")


class AccountStatus(BaseModel):
    """Detailed account status information."""

    customer_id: str = Field(..., description="Associated customer ID")
    state: AccountState = Field(..., description="Current account state")
    state_reason: str | None = Field(
        default=None,
        description="Reason for current state (e.g., overdue invoice, security concern)",
    )
    last_login: str | None = Field(default=None, description="Last known login date")
    mfa_enabled: bool = Field(default=False, description="Whether MFA is enabled")
    sso_enabled: bool = Field(default=False, description="Whether SSO is enabled")
    suspicious_activity: bool = Field(
        default=False, description="Whether suspicious activity was detected"
    )
    notes: str | None = Field(default=None, description="Additional account notes")


class Incident(BaseModel):
    """Known incident record."""

    incident_id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., description="Incident title")
    product_area: str = Field(..., description="Affected product area")
    status: Literal["investigating", "identified", "monitoring", "resolved"] = Field(
        ...,
        description="Current incident status",
    )
    severity: Literal["critical", "major", "minor"] = Field(
        ...,
        description="Incident severity",
    )
    description: str = Field(..., description="Incident description")
    started_at: str = Field(..., description="Incident start timestamp")
    resolved_at: str | None = Field(default=None, description="Incident resolution timestamp")
    affected_customers: list[str] = Field(
        default_factory=list,
        description="List of affected customer IDs (empty = all customers)",
    )


class Escalation(BaseModel):
    """Escalation record created by the system."""

    escalation_id: str = Field(..., description="Unique escalation identifier")
    ticket_id: str = Field(..., description="Associated ticket ID")
    destination_team: EscalationTeam = Field(..., description="Target team")
    priority: Priority = Field(..., description="Escalation priority")
    reason: str = Field(..., description="Escalation reason")
    agent_summary: str = Field(..., description="Agent-provided summary")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["pending", "acknowledged", "resolved"] = Field(default="pending")


class ToolActivityEvent(BaseModel):
    """Record of a tool invocation during agent execution."""

    event_id: str | None = Field(default=None)
    run_id: str = Field(..., description="Associated agent run ID")
    tool_name: str = Field(..., description="Name of the tool invoked")
    tool_input: dict[str, Any] = Field(default_factory=dict, description="Tool input parameters")
    tool_output_summary: str = Field(..., description="High-level summary of tool output")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: int | None = Field(default=None, description="Tool execution duration")


class AgentRun(BaseModel):
    """Metadata about an agent execution run."""

    run_id: str = Field(..., description="Unique run identifier")
    ticket_id: str = Field(..., description="Associated ticket ID")
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = Field(default=None)
    duration_ms: int | None = Field(default=None)
    final_status: ResolutionStatus | None = Field(default=None)
    tools_used: list[str] = Field(default_factory=list)
    failure_category: str | None = Field(default=None)
    is_demo: bool = Field(default=False, description="Whether this was a demo run")


class SupportDecision(BaseModel):
    """Structured output from the support agent."""

    ticket_id: str = Field(..., description="Associated ticket ID")
    customer_id: str | None = Field(
        default=None,
        description="Identified customer ID (null if not found)",
    )
    customer_name: str | None = Field(
        default=None,
        description="Identified customer company name",
    )
    category: SupportCategory = Field(..., description="Classified support category")
    priority: Priority = Field(..., description="Assigned priority")
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL, description="Detected sentiment")
    summary: str = Field(..., max_length=1000, description="Concise issue summary")
    identified_problem: str = Field(
        ...,
        max_length=2000,
        description="Specific problem identified by the agent",
    )
    investigation_summary: str = Field(
        ...,
        max_length=3000,
        description="Summary of investigation steps and findings",
    )
    resolution_status: ResolutionStatus = Field(..., description="Resolution decision")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)",
    )
    sla_minutes: int | None = Field(
        default=None,
        description="SLA in minutes (computed by service, not agent)",
    )
    reply_draft: str | None = Field(
        default=None,
        max_length=5000,
        description="Draft reply for the customer",
    )
    knowledge_sources: list[str] = Field(
        default_factory=list,
        description="Knowledge base sources used",
    )
    incident_id: str | None = Field(
        default=None,
        description="Associated incident ID if applicable",
    )
    escalation_required: bool = Field(
        default=False,
        description="Whether escalation is required",
    )
    escalation_team: EscalationTeam | None = Field(
        default=None,
        description="Target escalation team",
    )
    escalation_reason: str | None = Field(
        default=None,
        max_length=1000,
        description="Reason for escalation",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Information needed from the customer",
    )
    recommended_internal_action: str | None = Field(
        default=None,
        max_length=1000,
        description="Recommended action for internal team",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 2)

    @field_validator("escalation_team")
    @classmethod
    def validate_escalation_team(cls, v: EscalationTeam | None, info: Any) -> EscalationTeam | None:
        """Ensure escalation team is set when escalation is required."""
        data = info.data
        if data.get("escalation_required") and v is None:
            raise ValueError("escalation_team is required when escalation_required is True")
        return v

    @field_validator("escalation_reason")
    @classmethod
    def validate_escalation_reason(cls, v: str | None, info: Any) -> str | None:
        """Ensure escalation reason is set when escalation is required."""
        data = info.data
        if data.get("escalation_required") and not v:
            raise ValueError("escalation_reason is required when escalation_required is True")
        return v


class TicketResponse(BaseModel):
    """API response for a support ticket."""

    ticket_id: str = Field(..., description="Unique ticket identifier")
    customer_email: EmailStr = Field(..., description="Customer email")
    subject: str = Field(..., description="Ticket subject")
    message: str = Field(..., description="Ticket message")
    product_area: str | None = Field(default=None)
    status: Literal["open", "analyzed", "resolved", "escalated", "closed"] = Field(
        default="open",
    )
    priority: Priority | None = Field(default=None)
    category: SupportCategory | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    analyzed_at: datetime | None = Field(default=None)
    decision: SupportDecision | None = Field(default=None)
