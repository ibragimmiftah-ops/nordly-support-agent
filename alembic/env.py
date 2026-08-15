from logging.config import fileConfig
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def database_url() -> str:
    """Read DATABASE_URL without importing the application settings singleton."""
    import os

    value = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    if "{password}" in value:
        password_file = os.getenv("DATABASE_PASSWORD_FILE")
        if not password_file:
            raise RuntimeError(
                "DATABASE_PASSWORD_FILE is required when DATABASE_URL uses {password}"
            )
        password = Path(password_file).read_text(encoding="utf-8").strip()
        value = value.replace("{password}", quote(password, safe=""))
    if value.startswith("sqlite:///./"):
        value = f"sqlite:///{Path(value.removeprefix('sqlite:///')).resolve().as_posix()}"
    elif value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
    elif value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql+psycopg://", 1)
    return value


def run_migrations_offline() -> None:
    """Run migrations without opening a database connection."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
