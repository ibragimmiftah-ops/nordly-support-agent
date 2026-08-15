"""Prometheus metrics for agent execution."""

try:
    from prometheus_client import Counter, Histogram
except ImportError:  # pragma: no cover - exercised only in minimal deployments
    Counter = Histogram = None  # type: ignore[misc,assignment]


class _NoOpCollector:
    """Prometheus-compatible collector for minimal installations."""

    def labels(self, **_labels: str) -> "_NoOpCollector":
        """Accept metric labels."""
        return self

    def inc(self, _amount: float = 1.0) -> None:
        """Ignore a counter increment."""

    def observe(self, _amount: float) -> None:
        """Ignore a histogram observation."""


def _counter(name: str, description: str, labels: tuple[str, ...]) -> object:
    if Counter is None:
        return _NoOpCollector()
    return Counter(name, description, labels)


def _histogram(name: str, description: str, labels: tuple[str, ...]) -> object:
    if Histogram is None:
        return _NoOpCollector()
    return Histogram(name, description, labels)


class AgentMetrics:
    """Stable metric facade used by runners and services."""

    def __init__(self) -> None:
        """Create process-global Prometheus collectors."""
        self.runs = _counter("nordly_agent_runs_total", "Agent runs", ("runner", "outcome"))
        self.duration = _histogram(
            "nordly_agent_run_duration_seconds", "Agent run duration", ("runner",)
        )
        self.tokens = _counter("nordly_agent_tokens_total", "Provider tokens", ("model", "type"))
        self.cost = _counter("nordly_agent_cost_usd_total", "Estimated provider cost", ("model",))
        self.safety_events = _counter(
            "nordly_agent_safety_events_total", "Safety findings", ("kind", "severity")
        )
        self.errors = _counter("nordly_agent_errors_total", "Agent execution errors", ("runner",))
        self.http_requests = _counter(
            "nordly_http_requests_total",
            "HTTP requests",
            ("method", "route", "status"),
        )
        self.http_duration = _histogram(
            "nordly_http_request_duration_seconds",
            "HTTP request duration",
            ("method", "route"),
        )
        self.http_errors = _counter(
            "nordly_http_errors_total",
            "HTTP responses with error status",
            ("method", "route", "status"),
        )
        self.tickets = _counter("nordly_tickets_created_total", "Tickets created", ())
        self.escalations = _counter(
            "nordly_ticket_escalations_total", "Ticket escalations", ("team",)
        )
        self.budget_blocks = _counter(
            "nordly_agent_budget_blocks_total", "Live calls blocked by tenant budgets", ()
        )

    def record_usage(
        self, model: str, input_tokens: int, output_tokens: int, cost_usd: float = 0.0
    ) -> None:
        """Record token usage and externally calculated cost."""
        self.tokens.labels(model=model, type="input").inc(input_tokens)
        self.tokens.labels(model=model, type="output").inc(output_tokens)
        if cost_usd > 0:
            self.cost.labels(model=model).inc(cost_usd)


metrics = AgentMetrics()
