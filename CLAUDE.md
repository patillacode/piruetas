# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
just install        # install dependencies (uv sync --all-extras)
just dev            # run dev server with hot reload on :8000
just test           # run unit/integration tests (excludes e2e)
just test-cov       # tests with coverage report
just lint           # ruff check
just fix            # ruff check --fix + format
just install-e2e    # one-time: download Playwright browsers
just test-e2e       # run Playwright e2e tests (headless)
just test-e2e-headed  # e2e with visible browser
```

Run a single test file: `uv run pytest tests/test_entries.py -v`
Run a single test: `uv run pytest tests/test_entries.py::test_name -v`

For local dev: `cp .env.example .env`, set `SECRET_KEY` to any string and `SECURE_COOKIES=false`.

## Development

Feature worktrees live in `.worktrees/` (gitignored). Note: `CLAUDE.md` is also gitignored — it won't be present in new worktrees, create it manually if needed.

## Architecture

FastAPI + SQLModel + Jinja2 SSR app. No JS build step — frontend JS is vanilla.

**Entry point**: `app/main.py` — registers routers, mounts `/static`, sets up security headers (CSP with per-request nonce), and runs DB init + admin seeding on startup.

**Routers** (`app/routers/`):
- `auth.py` — login/logout, cookie-based sessions; rate limiting on login via `app/rate_limit.py` (failed-attempt tracking by IP)
- `journal.py` — day-per-page entries (CRUD), public share links
- `upload.py` — image upload/delete, files stored in `{data_dir}/uploads/`; orphaned images (uploaded but not saved in an entry, or from a deleted entry) are not automatically cleaned up
- `admin.py` — user management (admin-only)
- `account.py` — password change, account settings

**Auth flow**: signed session cookies (itsdangerous) with `session_version` field on `User` for invalidation. Three dependency tiers in `app/dependencies.py`: `get_current_user` (redirect to login), `get_current_user_optional` (public routes), `require_admin`. CSRF protection via `require_csrf` dependency on all state-mutating routes (logout, account, admin); login uses a separate cookie-based scheme (`LOGIN_CSRF_COOKIE`).

**Models** (`app/models.py`): `User`, `Entry` (one per user per date, unique constraint), `Image` (linked to entry + user).

**Settings** (`app/settings.py`): pydantic-settings, loaded from `.env`. Cached via `lru_cache`. Key vars: `SECRET_KEY`, `DATABASE_URL`, `DATA_DIR`, `SECURE_COOKIES`, `TRUST_PROXY`.

**i18n** (`app/i18n.py`): translations are hardcoded dicts (en/es); adding a locale means extending those dicts and the template locale switcher. Locale stored in cookie, resolved per-request and passed to all templates.

**Templates** (`app/templates/`): Jinja2, extend `layout.html`. CSP nonce injected via `templates_config.py`.

**Tests**: `tests/conftest.py` sets up an in-memory SQLite DB and async test client. E2E tests live in `tests/e2e/` and are excluded from the default `pytest` run.

Test-writing gotchas:
- E2e tests require system-level Playwright browser deps — do not run locally; they run in CI automatically
- `TestClient` is created with `follow_redirects=False` — auth-protected routes return 302, check `status_code` accordingly
- Use the `login()` and `get_csrf()` helpers from `conftest.py`; logging in requires a prior `GET /login` to obtain the CSRF cookie; `get_csrf()` also needed for account/admin/logout mutations
- `get_settings()` is `lru_cache` — set env overrides before app import, or call `get_settings.cache_clear()` between tests that change settings
