"""Authenticated FastAPI routes for Nordly Support Agent API."""

from typing import Annotated, Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agent.schemas import SupportTicketRequest
from app.auth.dependencies import require_principal, require_roles
from app.auth.models import Principal, Role
from app.auth.repository import AuthRepository
from app.auth.tokens import create_token
from app.database import get_connection
from app.repositories.audit_repository import AuditRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.escalation_repository import EscalationRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.privacy_repository import PrivacyRepository
from app.services.ticket_service import TicketService

router = APIRouter()
service = TicketService()

Authenticated = Annotated[Principal, Depends(require_principal)]
Writer = Annotated[Principal, Depends(require_roles(Role.ADMIN, Role.AGENT))]
Admin = Annotated[Principal, Depends(require_roles(Role.ADMIN))]


class LoginRequest(BaseModel):
    """Password login request."""

    tenant_id: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class RefreshRequest(BaseModel):
    """Refresh-token exchange request."""

    refresh_token: str = Field(min_length=20, max_length=4096)


class TicketStatusUpdate(BaseModel):
    """Request to update ticket status."""

    status: Literal["open", "analyzed", "resolved", "escalated", "closed"]


@router.get("/health")
async def health_check():
    """Return a public liveness response without business data."""
    return {"status": "healthy", "service": "nordly-support-agent"}


@router.get("/ready")
def readiness_check():
    """Confirm the database can execute a bounded query before accepting traffic."""
    try:
        with get_connection() as connection:
            row = connection.execute("SELECT 1 AS value").fetchone()
        value = row["value"] if row is not None and hasattr(row, "keys") else None
        if value != 1:
            raise RuntimeError("Unexpected database readiness result")
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "unavailable"},
        )
    return {"status": "ready", "database": "available"}


@router.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """Exchange valid demo or provisioned credentials for a JWT pair."""
    principal = AuthRepository.authenticate_password(
        request.tenant_id, request.username, request.password
    )
    if not principal:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    AuditRepository.record(principal.tenant_id, principal.subject, "login", "auth")
    return {
        "access_token": create_token(principal, "access"),
        "refresh_token": AuthRepository.create_refresh_session(principal),
        "token_type": "bearer",  # nosec B105
    }


@router.post("/api/v1/auth/refresh")
async def refresh(request: RefreshRequest):
    """Exchange a valid refresh JWT for a new access JWT."""
    try:
        rotated = AuthRepository.rotate_refresh_session(request.refresh_token)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None
    if not rotated:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    principal, refresh_token = rotated
    return {
        "access_token": create_token(principal, "access"),
        "refresh_token": refresh_token,
        "token_type": "bearer",  # nosec B105
    }


@router.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: RefreshRequest):
    """Revoke the supplied refresh session if it belongs to an active user."""
    try:
        revoked = AuthRepository.revoke_refresh_session(request.refresh_token)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None
    if not revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/api/v1/tickets")
async def create_ticket(request: SupportTicketRequest, principal: Writer):
    """Create a tenant-scoped support ticket."""
    ticket_id = service.create_ticket(
        customer_email=str(request.customer_email),
        subject=request.subject,
        message=request.message,
        product_area=request.product_area,
        tenant_id=principal.tenant_id,
    )
    AuditRepository.record(principal.tenant_id, principal.subject, "create", "ticket", ticket_id)
    return {"ticket_id": ticket_id, "status": "created"}


@router.post("/api/v1/tickets/{ticket_id}/analyze")
async def analyze_ticket(ticket_id: str, principal: Writer):
    """Analyze a tenant-scoped support ticket."""
    try:
        ticket = await service.analyze_ticket(ticket_id, principal.tenant_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Ticket not found") from None
    except Exception:
        raise HTTPException(status_code=500, detail="Analysis failed") from None
    AuditRepository.record(principal.tenant_id, principal.subject, "analyze", "ticket", ticket_id)
    return ticket


@router.get("/api/v1/tickets")
async def list_tickets(principal: Authenticated, limit: int = 50, offset: int = 0):
    """List tenant-scoped support tickets."""
    tickets = service.list_tickets(
        limit=max(1, min(limit, 100)), offset=max(0, offset), tenant_id=principal.tenant_id
    )
    return {"tickets": tickets, "count": len(tickets)}


@router.get("/api/v1/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, principal: Authenticated):
    """Get a ticket only from the authenticated tenant."""
    ticket = service.get_ticket(ticket_id, principal.tenant_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/api/v1/tickets/{ticket_id}/review")
async def review_ticket(ticket_id: str, update: TicketStatusUpdate, principal: Writer):
    """Update a ticket status within the authenticated tenant."""
    if not service.update_ticket_status(ticket_id, update.status, principal.tenant_id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    AuditRepository.record(
        principal.tenant_id,
        principal.subject,
        "review",
        "ticket",
        ticket_id,
        metadata={"status": update.status},
    )
    return {"ticket_id": ticket_id, "status": update.status}


@router.get("/api/v1/customers/{customer_id}")
async def get_customer(customer_id: str, principal: Authenticated):
    """Get a customer only from the authenticated tenant."""
    customer = CustomerRepository.get_by_id(customer_id, principal.tenant_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/api/v1/gdpr/customers/{customer_id}")
async def delete_customer_data(customer_id: str, principal: Admin):
    """Erase one tenant customer's related personal and business data."""
    deleted = PrivacyRepository.delete_customer(principal.tenant_id, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    AuditRepository.record(
        principal.tenant_id, principal.subject, "gdpr_delete", "customer", customer_id
    )
    return {"status": "deleted", "customer_id": customer_id}


@router.get("/api/v1/incidents")
async def list_incidents(principal: Authenticated, limit: int = 50):
    """List incidents for the authenticated tenant."""
    incidents = IncidentRepository.get_all_incidents(
        limit=max(1, min(limit, 100)), tenant_id=principal.tenant_id
    )
    return {"incidents": incidents}


@router.get("/api/v1/escalations")
async def list_escalations(principal: Authenticated, limit: int = 50, offset: int = 0):
    """List escalations for the authenticated tenant."""
    escalations = EscalationRepository.list_all(
        limit=max(1, min(limit, 100)),
        offset=max(0, offset),
        tenant_id=principal.tenant_id,
    )
    return {"escalations": escalations}
