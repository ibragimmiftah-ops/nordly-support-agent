"""Ticket service for orchestrating support ticket workflow.

Handles ticket creation, agent analysis, decision validation,
escalation creation, and audit trail recording.
"""

import uuid
from datetime import UTC, datetime

from app.agent.guardrails import check_prohibited_actions, validate_and_enforce
from app.agent.runner import get_runner
from app.agent.schemas import (
    AgentRun,
    Escalation,
    EscalationTeam,
    ResolutionStatus,
    TicketResponse,
)
from app.business_rules import calculate_sla_minutes
from app.observability import metrics
from app.repositories.agent_run_repository import AgentRunRepository, ToolEventRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.escalation_repository import EscalationRepository
from app.repositories.ticket_repository import TicketRepository
from app.services.memory_service import MemoryService


class TicketService:
    """Service for managing support tickets and agent analysis."""

    def __init__(self) -> None:
        """Initialize service with runner."""
        self.runner = get_runner()
        if hasattr(self.runner, "recall_context"):
            self.runner.recall_context = MemoryService.recall_context

    def create_ticket(
        self,
        customer_email: str,
        subject: str,
        message: str,
        product_area: str | None = None,
        tenant_id: str = "demo",
    ) -> str:
        """Create a new support ticket.

        Args:
            customer_email: Customer email address.
            subject: Ticket subject.
            message: Ticket message.
            product_area: Optional product area.
            tenant_id: Authenticated tenant boundary.

        Returns:
            Created ticket ID.
        """
        ticket_data = {
            "customer_email": customer_email,
            "subject": subject,
            "message": message,
            "product_area": product_area,
        }
        ticket_id = TicketRepository.create_ticket(ticket_data, tenant_id)
        metrics.tickets.inc()
        return ticket_id

    async def analyze_ticket(self, ticket_id: str, tenant_id: str = "demo") -> TicketResponse:
        """Analyze a ticket using the agent runner.

        Args:
            ticket_id: Ticket ID to analyze.
            tenant_id: Authenticated tenant boundary.

        Returns:
            Updated ticket response.
        """
        ticket = TicketRepository.get_ticket(ticket_id, tenant_id)
        if not ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")

        started_at = datetime.now(UTC)

        customer = CustomerRepository.get_by_email(ticket.customer_email, tenant_id)

        # Run agent analysis
        try:
            decision, events = await self.runner.analyze_ticket(
                ticket_id=ticket_id,
                customer_email=ticket.customer_email,
                subject=ticket.subject,
                message=ticket.message,
                product_area=ticket.product_area,
                tenant_id=tenant_id,
                customer_id=customer.customer_id if customer else None,
            )
        except Exception:
            metrics.errors.labels(runner="demo" if self.runner.is_demo else "openai").inc()
            raise
        run_id = events[0].run_id if events else f"run-{uuid.uuid4().hex[:12]}"

        completed_at = datetime.now(UTC)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Get customer plan for SLA calculation
        plan = customer.plan if customer else None

        # Validate and enforce business rules
        decision = validate_and_enforce(decision, plan.value if plan else None)

        # Calculate SLA deterministically
        if plan:
            decision.sla_minutes = calculate_sla_minutes(plan, decision.priority)

        # Check for prohibited actions
        violations = check_prohibited_actions(decision)
        if violations:
            decision.escalation_required = True
            decision.escalation_team = decision.escalation_team or EscalationTeam.SENIOR_SUPPORT
            decision.escalation_reason = f"Prohibited actions detected: {'; '.join(violations)}"
            decision.resolution_status = ResolutionStatus.ESCALATED

        # Store agent run metadata
        agent_run = AgentRun(
            run_id=run_id,
            ticket_id=ticket_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            final_status=decision.resolution_status,
            tools_used=[e.tool_name for e in events],
            is_demo=self.runner.is_demo,
        )
        AgentRunRepository.create(agent_run, tenant_id)
        ToolEventRepository.create_many(events, tenant_id)

        # Create escalation record if needed
        if decision.escalation_required:
            escalation = Escalation(
                escalation_id=f"esc-{uuid.uuid4().hex[:8]}",
                ticket_id=ticket_id,
                destination_team=decision.escalation_team,
                priority=decision.priority,
                reason=decision.escalation_reason or "Escalated by agent",
                agent_summary=decision.investigation_summary[:500],
            )
            EscalationRepository.create(escalation, tenant_id)
            metrics.escalations.labels(team=decision.escalation_team.value).inc()

        # Update ticket with decision
        TicketRepository.update_ticket_analysis(ticket_id, decision, tenant_id)

        if decision.customer_id:
            MemoryService.remember(
                tenant_id,
                decision.customer_id,
                f"{decision.category.value}: {decision.summary}. {decision.investigation_summary}",
                f"ticket:{ticket_id}",
                decision.confidence,
            )

        return TicketRepository.get_ticket(ticket_id, tenant_id)

    def get_ticket(self, ticket_id: str, tenant_id: str = "demo") -> TicketResponse | None:
        """Get ticket by ID.

        Args:
            ticket_id: Ticket ID.
            tenant_id: Authenticated tenant boundary.

        Returns:
            Ticket response or None.
        """
        return TicketRepository.get_ticket(ticket_id, tenant_id)

    def list_tickets(
        self, limit: int = 50, offset: int = 0, tenant_id: str = "demo"
    ) -> list[TicketResponse]:
        """List tickets with pagination.

        Args:
            limit: Maximum tickets to return.
            offset: Pagination offset.
            tenant_id: Authenticated tenant boundary.

        Returns:
            List of tickets.
        """
        return TicketRepository.get_tickets(limit, offset, tenant_id)

    def update_ticket_status(self, ticket_id: str, status: str, tenant_id: str = "demo") -> bool:
        """Update ticket status.

        Args:
            ticket_id: Ticket ID.
            status: New status.
            tenant_id: Authenticated tenant boundary.
        """
        return TicketRepository.update_ticket_status(ticket_id, status, tenant_id)
