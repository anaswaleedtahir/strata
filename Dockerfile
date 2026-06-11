# Stage 1: Builder - install deps, build CSS, collectstatic
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --group prod

# Copy app and build
COPY . .
RUN DJANGO_SETTINGS_MODULE=config.django.base \
    uv run python manage.py tailwind build --force

# Collectstatic using base settings (no database/AWS required for build)
RUN DJANGO_SETTINGS_MODULE=config.django.base \
    uv run python manage.py collectstatic --noinput

# Stage 2: Runtime - lean production image
FROM python:3.13-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser

WORKDIR /app

# Copy only .venv and staticfiles from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/staticfiles /app/staticfiles

# Copy application code
COPY --chown=appuser:appuser . /app/

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.django.production \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["sh", "-c", "gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers $((2 * $(nproc) + 1)) --access-logfile - --error-logfile - --log-level info"]
