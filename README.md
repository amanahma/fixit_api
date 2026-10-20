# Fixit API

Repair-ticket HTTP API for a fictional neighbourhood service. **Learning project only** — a booking API is not evidence that anyone wants Fixit, and it is not venture progress.

Live demos on free tiers sleep: a Render web service sleeps after ~15 minutes idle (wake-up ~1 minute) and Neon compute pauses after ~5 minutes idle. A slow first request is expected, not a breakage.

Auth is omitted on purpose.

## What it does

Customers book device-repair tickets. A ticket moves `NEW → ASSIGNED → IN_REPAIR → READY → DELIVERED`. `CANCELLED` is allowed from any status except `DELIVERED`. Service area is a configured list of districts. Districts come from the [India Post pincode API](https://api.postalpincode.in) (no key). Unknown pins still return HTTP 200 with `Status: "Error"` in the JSON; the app parses that.

## Architecture

```
Client → FastAPI (routers) → SQLAlchemy async session
                         ↘ PincodeClient → cache table → api.postalpincode.in
```

Postgres holds customers, technicians, tickets, and successful pincode lookups. Schema changes go through Alembic, never `create_all` in the running app.

## Endpoints

| Method | Path | Success |
| --- | --- | --- |
| GET | `/health` | 200 |
| GET | `/docs` | 200 |
| GET | `/serviceability/{pincode}` | 200 |
| POST | `/customers` | 201 |
| GET | `/customers` | 200 |
| GET | `/customers/{id}` | 200 |
| PATCH | `/customers/{id}` | 200 |
| DELETE | `/customers/{id}` | 204 |
| POST | `/technicians` | 201 |
| GET | `/technicians` | 200 |
| GET | `/technicians/{id}` | 200 |
| PATCH | `/technicians/{id}` | 200 |
| DELETE | `/technicians/{id}` | 204 |
| POST | `/tickets` | 201 |
| GET | `/tickets` | 200 |
| GET | `/tickets/{id}` | 200 |
| PATCH | `/tickets/{id}` | 200 |
| POST | `/tickets/{id}/assign` | 200 |
| POST | `/tickets/{id}/status` | 200 |
| POST | `/tickets/{id}/cancel` | 200 |

Errors are always `{"error": {"code", "message", "request_id"}}`. See `DESIGN.md` for the status/error tables.

## One-command local setup

Requires Docker Desktop (WSL2 backend on Windows).

```bash
docker compose up --build
```

API: http://localhost:8000/docs

Inside Compose the API reaches Postgres at hostname **`db`**, not `localhost`. Each container has its own network namespace; `localhost` inside the API container is the API container itself. Compose DNS resolves `db` to the Postgres service on the shared network.

Data:

- `docker compose down` then `up` — named volume `fixit_pgdata` still exists, data survives.
- `docker compose down -v` — the volume is deleted, data is gone.

Without Docker, copy `.env.example` to `.env`, run Postgres yourself, then:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

## Tests

Postgres is required (not SQLite). Compose creates `fixit_test` on first volume init.

This machine (and many Windows setups) already has Postgres on **5432**. Compose therefore publishes the learning database on **5433**. Pytest uses `127.0.0.1:5433` unless you set `TEST_DATABASE_URL`. Inside the Compose network the API still uses host `db` on port 5432.

```bash
docker compose up -d db
# wait until healthy
pytest
ruff check .
ruff format --check .
mypy
```

CI runs ruff, mypy, and pytest against a Postgres service on every push.

## Environment variables

| Name | Required | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | yes | SQLAlchemy URL. Compose API: `postgresql+asyncpg://fixit:fixit@db:5432/fixit`. Host pytest: port **5433**. |
| `SERVICE_DISTRICTS` | yes | Comma-separated district names (must match India Post `District`) |
| `PINCODE_API_BASE_URL` | no | Default `https://api.postalpincode.in` |
| `HTTP_TIMEOUT_SECONDS` | no | Default `5` |
| `PINCODE_MAX_RETRIES` | no | Extra attempts after the first, timeouts/5xx only. Default `2` |
| `LOG_LEVEL` | no | Default `INFO` |
| `SQL_ECHO` | no | `true` to log SQL (use this to inspect N+1) |
| `PORT` | no | Default `8000` |
| `ENABLE_ERROR_PROBE` | no | `true` enables `GET /debug/boom` (500) |

The process exits at startup if a required variable is missing. `.env` is gitignored; `.env.example` is committed.

Neon URLs often include `sslmode=require`. asyncpg does not accept that query flag; the app strips it and sets `ssl=True`.

## Deploy (Phase 8)

- Database: **Neon** free tier (not Render Postgres — Render’s free DB expires).
- App: **Render** free web service, build from this Dockerfile.
- Set env vars in the Render dashboard. Run `alembic upgrade head` against Neon (Render start command already runs migrations via `entrypoint.sh`).
- First requests are slow because of cold start / paused compute. Say so to reviewers.

Smoke against a live URL:

```bash
./scripts/smoke_test.sh https://YOUR-SERVICE.onrender.com
```

## Known limits

- No authentication.
- Free-tier cold starts.
- If the pincode API is down and the pin is not cached, customer create is rejected (502/504), not saved as unverified. Service area is a hard rule.
- This API is not a business.

## Phase 1 async script

```bash
python scripts/pincode_timing.py
python scripts/pincode_timing.py --break
```

`--break` puts `time.sleep(2)` inside a coroutine. `asyncio.gather` then waits ~2s extra for *all* lookups because `time.sleep` blocks the event loop. Use `await asyncio.sleep` (or don’t sleep) if you need concurrency.
