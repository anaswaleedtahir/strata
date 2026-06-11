# Property Hub Development Commands

# Start development services with Docker
up:
    docker compose -f docker-compose.yml up -d

# Stop development services
down:
    docker compose -f docker-compose.yml down -v

# Start uvicorn with Tailwind watch mode
runserver port="8000":
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT INT TERM
    uv run python manage.py tailwind watch &
    DJANGO_SETTINGS_MODULE=config.django.local uv run uvicorn config.asgi:application --reload --host 127.0.0.1 --port {{port}}

# Start uvicorn only (ASGI + WebSocket support)
uvicorn port="8000":
    DJANGO_SETTINGS_MODULE=config.django.local uv run uvicorn config.asgi:application --reload --host 127.0.0.1 --port {{port}}

# Start Tailwind watch mode only
tailwind-watch:
    uv run python manage.py tailwind watch

# Build production Tailwind CSS
build-css:
    uv run python manage.py tailwind build --force

# Create new Django migrations
makemigrations:
    uv run python manage.py makemigrations

# Apply Django migrations
migrate:
    uv run python manage.py migrate

# Install Python dependencies
build:
    uv sync

# Type check with ty (manual run)
type-check:
    uv run ty check .

# Show available commands
help:
    @just --list
