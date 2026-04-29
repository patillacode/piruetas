# Configuration Reference

All settings are read from environment variables (or an `.env` file).
Copy `.env.example` to get started: `cp .env.example .env`.

---

## Required

**`SECRET_KEY`**
Random string used to sign session cookies. Generate one with:
```bash
openssl rand -hex 32
```

---

## Application

**`ADMIN_USERNAME`** (default: `admin`)
Username for the admin account seeded at startup.

**`ADMIN_PASSWORD`** (default: `changeme`)
Password for the admin account. Change this before exposing the app.

**`REGISTRATION_OPEN`** (default: `false`)
When `true`, any visitor can create an account. When `false`, only the admin can create accounts via the admin panel.

**`PORT`** (default: `8000`)
Port the server listens on inside the container.

**`WEEK_START`** (default: `monday`)
Calendar week start day. Accepts `monday` or `sunday`.

---

## Storage

**`DATA_DIR`** (default: `/data`)
Directory used for the database file and image uploads. Mount this as a volume to persist data.

**`DATABASE_URL`** (default: `sqlite:////data/piruetas.db`)
SQLite connection string. Note the **four slashes**, three resolve the path relative to `/app` (inside the container) and would bypass the volume mount.

---

## Security

**`SECURE_COOKIES`** (default: `true`)
Sets the `Secure` flag on session cookies and enables HSTS headers. Set to `false` for any plain HTTP access — local development or a Docker deployment not behind TLS.

**`TRUST_PROXY`** (default: `false`)
When `true`, reads the real client IP from the `X-Forwarded-For` header for rate limiting. Enable this when running behind a reverse proxy (nginx, Caddy, Traefik).

> **Warning:** only enable if you control the proxy. Without a proxy in front, attackers can spoof `X-Forwarded-For` to bypass rate limiting.

---

## Demo mode

**`DEMO_ENABLED`** (default: `false`)
Enables a demo account and periodic content reset. Useful for public showcases.

**`DEMO_USERNAME`** (default: `demo`)
Username for the demo account.

**`DEMO_PASSWORD`** (default: `demo`)
Password for the demo account.

**`DEMO_RESET_INTERVAL`** (default: `1800`)
Seconds between automatic demo content wipes.
