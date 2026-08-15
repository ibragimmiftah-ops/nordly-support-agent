"""Application configuration using pydantic-settings."""

from pathlib import Path
from urllib.parse import quote

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application mode
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")

    # OpenAI configuration
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_api_key_file: str | None = Field(default=None, alias="OPENAI_API_KEY_FILE")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    agent_max_turns: int = Field(default=10, alias="AGENT_MAX_TURNS", ge=1, le=50)
    agent_timeout_seconds: float = Field(default=30.0, alias="AGENT_TIMEOUT_SECONDS", gt=0, le=300)
    agent_max_tool_calls: int = Field(default=12, alias="AGENT_MAX_TOOL_CALLS", ge=1, le=100)
    agent_max_duplicate_tool_calls: int = Field(
        default=2, alias="AGENT_MAX_DUPLICATE_TOOL_CALLS", ge=1, le=10
    )
    openai_input_cost_per_million: float = Field(
        default=0.15, alias="OPENAI_INPUT_COST_PER_MILLION", ge=0
    )
    openai_output_cost_per_million: float = Field(
        default=0.60, alias="OPENAI_OUTPUT_COST_PER_MILLION", ge=0
    )
    daily_budget_usd: float = Field(default=10.0, alias="DAILY_BUDGET_USD", ge=0)
    weekly_budget_usd: float = Field(default=50.0, alias="WEEKLY_BUDGET_USD", ge=0)

    # Database
    database_url: str = Field(
        default="sqlite:///./data/nordly.db",
        alias="DATABASE_URL",
    )
    database_password_file: str | None = Field(default=None, alias="DATABASE_PASSWORD_FILE")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    cache_ttl_seconds: int = Field(default=300, alias="CACHE_TTL_SECONDS", ge=0)

    @staticmethod
    def _read_secret(path: str, name: str) -> str:
        value = Path(path).read_text(encoding="utf-8").strip()
        if not value:
            raise ValueError(f"{name} must not be empty")
        return value

    @model_validator(mode="after")
    def resolve_secret_files(self) -> "Settings":
        """Resolve Docker-style secrets and reject unsafe production defaults."""
        if "{password}" not in self.database_url:
            pass
        elif not self.database_password_file:
            raise ValueError("DATABASE_PASSWORD_FILE is required when DATABASE_URL uses {password}")
        else:
            password = self._read_secret(self.database_password_file, "DATABASE_PASSWORD_FILE")
            self.database_url = self.database_url.replace("{password}", quote(password, safe=""))
        if self.openai_api_key_file:
            self.openai_api_key = self._read_secret(self.openai_api_key_file, "OPENAI_API_KEY_FILE")
        if self.jwt_secret_file:
            self.jwt_secret = self._read_secret(self.jwt_secret_file, "JWT_SECRET_FILE")
        if self.bootstrap_admin_password_file:
            self.bootstrap_admin_password = self._read_secret(
                self.bootstrap_admin_password_file, "BOOTSTRAP_ADMIN_PASSWORD_FILE"
            )
        if self.encryption_key_file:
            self.encryption_key = self._read_secret(self.encryption_key_file, "ENCRYPTION_KEY_FILE")
        if self.metrics_token_file:
            self.metrics_token = self._read_secret(self.metrics_token_file, "METRICS_TOKEN_FILE")
        if not self.demo_mode and self.jwt_secret == self.default_jwt_secret:
            raise ValueError("JWT_SECRET or JWT_SECRET_FILE must be configured in production")
        if not self.demo_mode and not self.redis_url:
            raise ValueError("REDIS_URL is required in production")
        if not self.demo_mode and not self.encryption_key_file:
            raise ValueError("ENCRYPTION_KEY_FILE is required in production")
        if not self.demo_mode and not self.metrics_token:
            raise ValueError("METRICS_TOKEN or METRICS_TOKEN_FILE is required in production")
        return self

    # Knowledge base
    knowledge_base_path: str = Field(
        default="./knowledge_base",
        alias="KNOWLEDGE_BASE_PATH",
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(
        default="nordly-support-agent", alias="OTEL_SERVICE_NAME", min_length=1
    )

    # Security. Production deployments must override secrets and demo credentials.
    jwt_secret: str = Field(
        default="demo-only-jwt-secret-change-before-production-32-bytes",
        alias="JWT_SECRET",
    )
    jwt_secret_file: str | None = Field(default=None, alias="JWT_SECRET_FILE")
    bootstrap_admin_username: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_tenant: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_TENANT")
    bootstrap_admin_password: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_PASSWORD")
    bootstrap_admin_password_file: str | None = Field(
        default=None, alias="BOOTSTRAP_ADMIN_PASSWORD_FILE"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_minutes: int = Field(default=15, alias="ACCESS_TOKEN_MINUTES", ge=1)
    refresh_token_days: int = Field(default=7, alias="REFRESH_TOKEN_DAYS", ge=1)
    demo_tenant_id: str = Field(default="demo", alias="DEMO_TENANT_ID")
    demo_admin_username: str = Field(default="demo-admin", alias="DEMO_ADMIN_USERNAME")
    demo_admin_password: str = Field(
        default="Demo-Admin-Password-Change-Me!", alias="DEMO_ADMIN_PASSWORD"
    )
    demo_api_key: str = Field(
        default="demo-api-key-change-me-4e6546aa9ca74d4e", alias="DEMO_API_KEY"
    )
    https_redirect: bool = Field(default=False, alias="HTTPS_REDIRECT")
    hsts_max_age_seconds: int = Field(default=31_536_000, alias="HSTS_MAX_AGE_SECONDS", ge=0)
    rate_limit_requests: int = Field(default=120, alias="RATE_LIMIT_REQUESTS", ge=1)
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS", ge=1)
    max_estimated_call_cost_usd: float = Field(
        default=0.05, alias="MAX_ESTIMATED_CALL_COST_USD", gt=0
    )
    encryption_key: str | None = Field(default=None, alias="ENCRYPTION_KEY")
    encryption_key_file: str | None = Field(default=None, alias="ENCRYPTION_KEY_FILE")
    metrics_token: str | None = Field(default=None, alias="METRICS_TOKEN")
    metrics_token_file: str | None = Field(default=None, alias="METRICS_TOKEN_FILE")
    memory_retention_days: int = Field(default=30, alias="MEMORY_RETENTION_DAYS", ge=1)
    audit_retention_days: int = Field(default=365, alias="AUDIT_RETENTION_DAYS", ge=1)
    tool_event_retention_days: int = Field(default=90, alias="TOOL_EVENT_RETENTION_DAYS", ge=1)

    # CORS
    cors_origins: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000",
        alias="CORS_ORIGINS",
    )

    @property
    def is_demo_mode(self) -> bool:
        """Return whether the application is running in demo mode."""
        return self.demo_mode

    @property
    def default_jwt_secret(self) -> str:
        """Return the known demo-only JWT secret for validation and diagnostics."""
        return "demo-only-jwt-secret-change-before-production-32-bytes"

    @property
    def production_bootstrap_configured(self) -> bool:
        """Return whether all explicit one-time production bootstrap values exist."""
        return all(
            (
                self.bootstrap_admin_username,
                self.bootstrap_admin_tenant,
                self.bootstrap_admin_password,
            )
        )

    @property
    def has_openai_key(self) -> bool:
        """Return whether an OpenAI API key is configured."""
        return self.openai_api_key is not None and len(self.openai_api_key) > 0

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def knowledge_base_dir(self) -> Path:
        """Return the knowledge base directory as a Path object."""
        return Path(self.knowledge_base_path)


# Global settings instance
settings = Settings()
