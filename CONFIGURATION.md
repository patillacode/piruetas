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

---

## Notifications

Piruetas can send alerts to ntfy and/or Telegram when security-relevant events occur. Both channels are optional and independent — configure one or both.

**Events notified:**
- New user signup
- Admin account login
- IP address blocked by rate limiter (10 failed attempts in 15 minutes)

**`NTFY_URL`** (default: empty — disabled)
Full ntfy topic URL, e.g. `https://ntfy.sh/my-secret-topic`. Leave empty to disable.

**`TELEGRAM_BOT_TOKEN`** (default: empty — disabled)
Telegram bot token from @BotFather. Both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` must be set for Telegram notifications to fire.

**`TELEGRAM_CHAT_ID`** (default: empty — disabled)
Telegram chat or channel ID to send messages to.

> Notification failures are silently logged and never affect request handling.

---

## Scheduled Tasks

| Setting | Default | Description |
|---|---|---|
| `CLEANUP_SCHEDULE` | `0 3 * * *` | Orphaned image cleanup — daily at 3am |
| `VACUUM_SCHEDULE` | `0 3 * * 0` | SQLite VACUUM — weekly Sunday at 3am |
| `STORAGE_SCHEDULE` | `0 4 * * *` | Per-user storage recalculation — daily at 4am |

All values are standard cron expressions.
