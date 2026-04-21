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

# Run E2E tests with Playwright
test-e2e:
    uv run pytest tests/e2e/ -v

# Run E2E tests with visible browser (for debugging)
test-e2e-headed:
    uv run pytest tests/e2e/ -v --headed

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

# Install Playwright browsers for E2E tests (one-time setup)
install-e2e:
    uv sync --extra e2e
    uv run playwright install chromium firefox

# List recent tags (no args) or tag a release with notes (just release 1.2.3)
release version="":
    #!/usr/bin/env bash
    if [ -z "{{version}}" ]; then
        echo "Recent tags:"
        git tag --sort=-v:refname | head -10
    else
        LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
        echo "=== Recent tags ==="
        git tag --sort=-v:refname | head -5
        echo ""
        echo "=== Release notes for v{{version}} ==="
        if [ -n "$LAST_TAG" ]; then
            git log "${LAST_TAG}..HEAD" --oneline
        else
            git log --oneline -20
        fi
        echo ""
        echo "Tagging v{{version}} and pushing..."
        git tag v{{version}}
        git push origin v{{version}}
        echo "Done — CI will build and push the Docker image"
    fi

# Show recent git log
log:
    git log --oneline -20
