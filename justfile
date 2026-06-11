# Property Hub Development Commands

# Start development services with Docker
up:
    docker compose -f docker-compose.yml up -d

# Stop development services
down:
    docker compose -f docker-compose.yml down -v

# Start Django development server with Tailwind watch mode
runserver port="8000":
    uv run python manage.py tailwind runserver {{port}}

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
