"""Historical ticket lookup tool.

Bounded: only returns tickets for the identified customer email.
"""

from typing import Any

from app.repositories.ticket_repository import TicketRepository


def get_previous_tickets(
    customer_email: str, limit: int = 5, tenant_id: str = "demo"
) -> list[dict[str, Any]]:
    """Get previous tickets for a customer.

    Args:
        customer_email: Customer email address.
        limit: Maximum number of tickets to return.
        tenant_id: Authenticated tenant boundary.

    Returns:
        List of previous ticket summaries.
    """
    return TicketRepository.get_previous_tickets(customer_email, max(1, min(limit, 20)), tenant_id)
