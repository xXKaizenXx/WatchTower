# Deploying WatchTower to Production

WatchTower runs as **three processes** plus managed Postgres and Redis:

| Process | Role | Start command |
|---------|------|----------------|
| **API** | Heartbeats + admin REST | `uvicorn` / `/start-api.sh` |
| **Celery worker** | Incident handling + alerts | `celery -A app.workers.celery_app worker -Q watchtower` |
| **Redis listener** | TTL expiry → Celery | `python -m app.listeners.redis_expiry` |

All three share the same Docker image.

---

## Pre-deploy checklist

- [ ] Generate `WATCHTOWER_API_KEY` (≥32 chars):  
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `CORS_ORIGINS` to your real domain(s) — not `*`
- [ ] Set `TRUSTED_HOSTS` to your API hostname(s)
- [ ] Use managed **PostgreSQL** and **Redis** (Redis must allow `notify-keyspace-events Ex`)
- [ ] Run migrations: `alembic upgrade head` (automatic via container entrypoint)
- [ ] Configure Slack/Twilio env vars if using alerts
- [ ] Point cron jobs at `POST https://your-api/ping/{id}` with `X-Ping-Token`

---

## Docker Compose (VPS / single server)

```bash
cp .env.production.example .env
# Fill in secrets and URLs

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Put **nginx** or **Caddy** in front for HTTPS and proxy to port `8000`.

---

## Render.com

Deploy **three services** from the same repo (Docker or Python):

1. **Web Service** — `watchtower-api`  
   - Start: `/start-api.sh` (or Dockerfile default)  
   - Health: `/health`  
   - Env: `ENVIRONMENT=production`, `DATABASE_URL`, `REDIS_URL`, `WATCHTOWER_API_KEY`, …

2. **Background Worker** — Celery  
   - Start: `celery -A app.workers.celery_app worker -Q watchtower -l info`

3. **Background Worker** — Redis listener  
   - Start: `python -m app.listeners.redis_expiry`

Add **PostgreSQL** and **Redis** add-ons. For Redis on Render, confirm keyspace notifications are enabled (or use Upstash/Redis Cloud with `notify-keyspace-events Ex`).

See `render.yaml` for a blueprint starter.

---

## Railway

Same three services pattern:

- Service 1: API (public networking, `PORT` injected automatically)
- Service 2: Celery worker
- Service 3: Listener

Add Postgres + Redis plugins; reference `${{Postgres.DATABASE_URL}}` in variables (convert to `postgresql+asyncpg://` for async URL).

---

## Fly.io

```bash
fly launch
fly postgres create
fly redis create   # ensure keyspace events enabled
fly secrets set WATCHTOWER_API_KEY=... ENVIRONMENT=production ...
fly deploy
```

Scale Celery and listener as separate `fly scale` processes or Machines.

---

## Portfolio demo (live URL)

1. Deploy API to Render/Railway (free tier).
2. Add **README badge** or link: `Live API: https://your-app.onrender.com/health`
3. Keep `/docs` off in production; use recorded GIF or local Swagger for demos.
4. Optional: enable docs temporarily with `ENABLE_DOCS=true` for reviewer access.

---

## Health probes (Kubernetes / PaaS)

| Probe | Path | Expects |
|-------|------|---------|
| Liveness | `GET /health` | 200 |
| Readiness | `GET /ready` | 200 (DB + Redis up) |

---

## Security notes

- Ping tokens are SHA-256 hashed; shown once at service creation.
- Admin routes require `X-API-Key`.
- `/ping` is rate-limited (`PING_RATE_LIMIT`, default `120/minute`).
- Production boot **fails** if API key is weak or CORS is `*`.
