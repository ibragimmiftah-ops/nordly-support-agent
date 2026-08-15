"""Incident lookup tool for the support agent.

Bounded: returns only active incidents, optionally filtered by product area.
"""

from app.agent.schemas import Incident
from app.repositories.incident_repository import IncidentRepository


def check_active_incidents(
    product_area: str | None = None, limit: int = 10, tenant_id: str = "demo"
) -> list[Incident]:
    """Check for active incidents.

    Args:
        product_area: Optional product area to filter by.
        limit: Maximum number of incidents to return.
        tenant_id: Authenticated tenant boundary.

    Returns:
        List of active incidents.
    """
    return IncidentRepository.get_active_incidents(product_area, limit, tenant_id)
