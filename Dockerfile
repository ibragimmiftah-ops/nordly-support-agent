# syntax=docker/dockerfile:1.7
FROM python:3.12.5-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /build

COPY requirements-production.txt constraints.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip==26.2.1 \
    && /opt/venv/bin/pip install --requirement requirements-production.txt

FROM python:3.12.5-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEMO_MODE=true \
    DATABASE_URL=sqlite:////var/lib/nordly/nordly.db \
    KNOWLEDGE_BASE_PATH=/app/knowledge_base \
    LOG_LEVEL=INFO

RUN groupadd --system --gid 10001 nordly \
    && useradd --system --uid 10001 --gid nordly --home-dir /nonexistent --shell /usr/sbin/nologin nordly \
    && mkdir -p /app /var/lib/nordly \
    && chown -R nordly:nordly /var/lib/nordly

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=nordly:nordly app ./app
COPY --chown=nordly:nordly data ./data
COPY --chown=nordly:nordly knowledge_base ./knowledge_base
COPY --chown=nordly:nordly alembic ./alembic
COPY --chown=nordly:nordly alembic.ini ./alembic.ini

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]

FROM debian:bookworm-slim AS backup

RUN apt-get update \
    && apt-get install --yes --no-install-recommends age ca-certificates postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10002 backup \
    && useradd --system --uid 10002 --gid backup --home-dir /backups --shell /usr/sbin/nologin backup \
    && mkdir -p /backups \
    && chown backup:backup /backups
COPY --chown=backup:backup scripts/backup.sh /usr/local/bin/nordly-backup
COPY --chown=backup:backup scripts/backup-scheduled.sh /usr/local/bin/nordly-backup-scheduled
RUN chmod 0555 /usr/local/bin/nordly-backup /usr/local/bin/nordly-backup-scheduled
USER 10002:10002
CMD ["/usr/local/bin/nordly-backup"]
