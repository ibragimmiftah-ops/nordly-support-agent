"""Command-line interface for Nordly Support Agent."""

import asyncio
import sys

from app.services.ticket_service import TicketService


def main() -> int:
    """Main CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] != "analyze":
        print(
            "Usage: python -m app.cli analyze --email <email> --subject <subject> "
            "--message <message>"
        )
        return 1

    # Parse arguments
    email = None
    subject = None
    message = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--email" and i + 1 < len(sys.argv):
            email = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--subject" and i + 1 < len(sys.argv):
            subject = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--message" and i + 1 < len(sys.argv):
            message = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if not all([email, subject, message]):
        print("Error: --email, --subject, and --message are required")
        return 1

    service = TicketService()

    # Create ticket
    ticket_id = service.create_ticket(
        customer_email=email,
        subject=subject,
        message=message,
    )
    print(f"Created ticket: {ticket_id}")

    # Analyze ticket
    result = asyncio.run(service.analyze_ticket(ticket_id))
    print(f"Analysis complete. Status: {result.status}")
    if result.decision:
        print(f"Category: {result.decision.category.value}")
        print(f"Priority: {result.decision.priority.value}")
        print(f"Confidence: {result.decision.confidence}")
        print(f"Resolution: {result.decision.resolution_status.value}")
        if result.decision.escalation_required:
            print(f"Escalated to: {result.decision.escalation_team.value}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
