#!/usr/bin/env just
set dotenv-load := true

# List available commands
default:
    @just --list

# Install dependencies in virtual environment
install:
    uv sync --all-extras

# Run development server with hot reload
dev:
    uv run uvicorn app.main:app --reload --port ${PORT:-8000}

# Run linter
lint:
    uv run ruff check app/ tests/

# Auto-fix formatting and import ordering
fix:
    uv run ruff check --fix app/ tests/
    uv run ruff format app/ tests/

# Format code
format:
    uv run ruff format app/ tests/

# Run tests
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest --cov=app --cov-report=term-missing

# Build Docker image locally
docker-build:
    docker build -t piruetas .

# Run app in Docker using .env file
docker-run:
    docker run --rm \
        --env-file .env \
        -v $(pwd)/data:/data \
        -p ${PORT:-8000}:8000 \
        piruetas

# Start with Docker Compose
compose-up:
    docker compose up -d

# Stop Docker Compose
compose-down:
    docker compose down

# View Docker Compose logs
compose-logs:
    docker compose logs -f

# Create admin user from env vars (idempotent)
seed-admin:
    uv run python scripts/seed_admin.py

# Open SQLite shell on the data file
db-shell:
    sqlite3 ${DATABASE_URL#sqlite:////}

# Tag a release and push to trigger CI build
release version:
    git tag v{{version}}
    git push origin v{{version}}
    @echo "Released v{{version}} — CI will build and push the Docker image"

# Show recent git log
log:
    git log --oneline -20
