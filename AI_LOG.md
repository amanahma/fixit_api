# AI log

Curriculum M0.6: prompt, what changed, what was rejected.

## 2026-10-20 — full curriculum build

**Prompt:** Implement the Fixit Express repair-ticket learning API (phases 0–10), empty GitHub repo `amanahma/fixit_api`.

**What changed:** DESIGN.md first, then ticket rules, FastAPI routers, SQLAlchemy 2 async + Alembic, pincode client with cache/retries/respx tests, config/logging/CI, Docker Compose, smoke script, README.

**Later:** tests failed with `InvalidPasswordError`. Cause was `str(make_url())` redacting the DB password, plus host port 5432 already taken by PostgreSQL 18. Rejected “just mock the DB / switch tests to SQLite.”

**Rejected from typical agent defaults:**

- `Base.metadata.create_all` in the app (Alembic only).
- SQLite for tests (Postgres only).
- Saving an “unverified” customer when the pincode API is down (reject 502/504; service area is a hard rule).
- Treating India Post HTTP 200 as success without reading `Status`.
- Retrying parsed `Status: Error` / 4xx.
- Extra repository/service/factory layers around three tables.
- Copying `.env` into the image; running the container as root.
- Mocking `check_transition` inside the tests that are supposed to prove it.

**Hand-first rule:** this session implemented the first of each pattern because the prompt asked for the whole build. Rewrite these yourself before treating the repo as “I learned it”: `app/services/ticket_rules.py`, `app/routers/customers.py`, `migrations/versions/0001_initial.py`, `app/services/pincode_client.py`, `app/errors.py`, `Dockerfile`.

## 2026-10-21 — Antigravity session: resume after Cursor limit and resolve blockers

**Prompt:** Inspect Cursor's progress, diagnose remaining failures, and resume the build.

**What was discovered broken:**
1. `MissingGreenlet` in response serialization (`updated_at`): `session.flush()` expired `updated_at` (server `onupdate=func.now()`). FastAPI serialization triggered implicit async lazy-load outside greenlet.
2. Event loop mismatch in pytest teardown (`NoneType has no attribute 'send'`): `asyncio_default_fixture_loop_scope = "session"` in `pyproject.toml` ran fixtures across multiple event loops on Windows proactor.
3. `test_unhandled_is_generic_500` failed: `ASGITransport` defaulted to `raise_app_exceptions=True`, bubbling the 500 probe out of ASGI.
4. Docker entrypoint failure: Windows CRLF in `entrypoint.sh` caused `exec ./entrypoint.sh: no such file or directory`.
5. Git repository was not initialized on disk (`.git` absent).

**What changed:**
- Added `await session.refresh(...)` after `session.flush()` across `tickets`, `customers`, and `technicians` routes.
- Switched `asyncio_default_fixture_loop_scope` to `"function"` in `pyproject.toml`.
- Set `raise_app_exceptions=False` in `tests/conftest.py` `client` fixture.
- Converted `entrypoint.sh` and scripts to LF line endings.
- Verified 60/60 pytest passing, 0 ruff errors, 0 mypy errors.
- Built and validated Docker Compose containers, testing live API queries (`/health`, `/customers`, `/tickets`, 409 conflict, 422 pincode).
- Initialized git repository (`git init -b main`) and added remote `origin`.
