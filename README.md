# WatchTower

**Distributed system health & security watchdog** — a production-grade dead man's switch for microservices, cron jobs, and background workers.

Traditional uptime monitors only ask *"is the server returning HTTP 200?"* WatchTower answers a harder question: **did your critical background process actually finish on schedule?**

External services **push** heartbeats to WatchTower. Redis TTL expiry detects silence in milliseconds. A tiered escalation pipeline logs incidents, fires Slack/Discord webhooks, and sends Twilio SMS for production-critical failures — all behind circuit breakers so alert storms don't take down your on-call.

---

## Architecture

```
[Cron / Worker] --POST /ping/{id}--> [ FastAPI API ]
                                         |
                         +---------------+---------------+
                         |                               |
                   [ Redis TTL ]                  [ PostgreSQL ]
                   heartbeat keys                  services + incidents
                         |
                  (key expires)
                         |
              [ Redis Expiry Listener ]
                         |
                   [ Celery Worker ]
                         |
              [ Slack / Discord / Twilio SMS ]
```

| Component | Role |
|-----------|------|
| **FastAPI** | Inverted health check — services ping *you* |
| **Redis** | TTL-based silence detection (`SET key EX ttl`) |
| **PostgreSQL** | Service registry, incident history, audit trail |
| **Celery** | Async incident processing & escalation |
| **Listener** | Subscribes to Redis `__keyevent@0__:expired` |
| **Circuit breaker** | Protects webhook/SMS providers from cascade failures |

---

## Quick start (Docker)

```bash
cp .env.example .env
# Set WATCHTOWER_API_KEY in .env

docker compose up --build
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  
- Readiness: http://localhost:8000/ready  

### Register a monitored service

```bash
curl -X POST http://localhost:8000/api/v1/services \
  -H "X-API-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nightly Financial Report",
    "environment": "production",
    "heartbeat_interval": 86400,
    "grace_period": 3600,
    "enable_sms_alerts": true,
    "webhook_url": "https://hooks.slack.com/services/..."
  }'
```

Save the returned `ping_token` — it is shown **once**.

### Send a heartbeat (from your cron job)

```bash
curl -X POST http://localhost:8000/ping/{service_id} \
  -H "X-Ping-Token: YOUR_PING_TOKEN"
```

See `examples/cron_ping.sh` for a cron-ready template.

---

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Start Postgres + Redis (or use docker compose up postgres redis)
alembic upgrade head
uvicorn app.main:app --reload

# Separate terminals:
celery -A app.workers.celery_app worker -Q watchtower -l info
python -m app.listeners.redis_expiry
```

```bash
pytest tests/ -v --cov=app
ruff check app tests
bandit -r app
```

---

## Security model

| Endpoint | Auth |
|----------|------|
| `POST /ping/{id}` | Per-service `X-Ping-Token` (SHA-256 hashed at rest) |
| `/api/v1/*` | Global `X-API-Key` header |
| `/health`, `/docs` | Public |

---

## Escalation tiers

1. **Database** — incident row created, service marked `UNHEALTHY`
2. **Webhook** — Slack or Discord (per-service URL or global env fallback)
3. **SMS** — Twilio, only for `production` services with `enable_sms_alerts: true`

Circuit breakers trip after repeated notification failures and auto-recover.

---

## Production deployment

Local Docker uses `ENVIRONMENT=development` (Swagger at `/docs`). For production:

1. Copy `.env.production.example` → `.env` and fill secrets.
2. Run: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
3. Read **[DEPLOYMENT.md](DEPLOYMENT.md)** for Render, Railway, Fly.io, and HTTPS.

Production hardening includes:

- Boot-time rejection of weak API keys and `CORS_ORIGINS=*`
- `/docs` disabled by default (`ENABLE_DOCS=true` to override)
- Security headers, request IDs, ping rate limiting
- Container healthchecks and `restart: unless-stopped`
- DB connection pooling

### Portfolio checklist

- [ ] Deploy API + worker + listener (see DEPLOYMENT.md)
- [ ] Add live `/health` URL to README
- [ ] Record a 60s demo: register service → ping → miss heartbeat → incident
- [ ] Pin GitHub repo with CI badge passing

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):

- Ruff lint + format
- **Bandit** SAST scan
- **Safety** dependency audit
- Pytest with coverage
- Docker image build

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `WATCHTOWER_API_KEY` | Admin API authentication |
| `DATABASE_URL` | Async Postgres URL |
| `REDIS_URL` | Heartbeat TTL store |
| `SLACK_WEBHOOK_URL` | Global Slack fallback |
| `TWILIO_*` | SMS for critical alerts |

Full list in `.env.example`.

---

## Tech stack

Python 3.12 · FastAPI · SQLModel · PostgreSQL · Redis · Celery · Alembic · Docker · GitHub Actions · Bandit · Twilio · structlog

---

## License

MIT
