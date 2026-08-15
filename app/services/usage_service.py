"""Deterministic provider pricing and budget enforcement."""

from app.config import settings
from app.database import init_database
from app.observability import metrics
from app.repositories.usage_repository import UsageRepository


class UsageService:
    """Check budgets before calls and account actual usage afterward."""

    @staticmethod
    def calculate_cost(input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost from configured per-million-token rates."""
        return (
            input_tokens * settings.openai_input_cost_per_million
            + output_tokens * settings.openai_output_cost_per_million
        ) / 1_000_000

    @staticmethod
    def budget_available(tenant_id: str) -> bool:
        """Return false when either rolling tenant budget is exhausted."""
        # Direct runner/CLI use does not necessarily pass through FastAPI lifespan.
        init_database()
        daily, weekly = UsageRepository.current_spend(tenant_id)
        allowed = daily < settings.daily_budget_usd and weekly < settings.weekly_budget_usd
        if not allowed:
            metrics.budget_blocks.inc()
        return allowed

    @staticmethod
    def reserve(tenant_id: str) -> str | None:
        """Atomically reserve the configured maximum cost for one provider call."""
        init_database()
        reservation = UsageRepository.reserve(
            tenant_id,
            settings.max_estimated_call_cost_usd,
            settings.daily_budget_usd,
            settings.weekly_budget_usd,
        )
        if reservation is None:
            metrics.budget_blocks.inc()
        return reservation

    @classmethod
    def record(cls, tenant_id: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Persist usage and publish aggregate metrics without tenant labels."""
        cost = cls.calculate_cost(input_tokens, output_tokens)
        UsageRepository.record(tenant_id, model, input_tokens, output_tokens, cost)
        metrics.record_usage(model, input_tokens, output_tokens, cost)
        return cost

    @classmethod
    def finalize(
        cls,
        reservation_id: str,
        tenant_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        customer_id: str | None = None,
    ) -> float:
        """Finalize reserved capacity with actual provider usage."""
        cost = cls.calculate_cost(input_tokens, output_tokens)
        UsageRepository.finalize(
            reservation_id, tenant_id, model, input_tokens, output_tokens, cost, customer_id
        )
        metrics.record_usage(model, input_tokens, output_tokens, cost)
        return cost

    @staticmethod
    def release(reservation_id: str, tenant_id: str) -> None:
        """Release an unused provider reservation."""
        UsageRepository.release(reservation_id, tenant_id)
