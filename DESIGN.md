# Fixit API — design (one page)

Learning project: a repair-ticket HTTP API. Not a product launch and not venture progress.

## Resources

| Resource | Fields |
| --- | --- |
| **customers** | `id`, `name`, `phone` (unique, 10 digits starting 6–9), `pincode` (6 digits), `district` (from India Post, not client input), timestamps |
| **technicians** | `id`, `name`, `phone`, `active` (bool), timestamps |
| **tickets** | `id`, `customer_id`, `technician_id` (optional until assign), `device`, `issue`, `status`, `quoted_price` (optional), timestamps |
| **pincode_cache** | `pincode` (PK), `districts` (JSON list), `fetched_at` — successful lookups only |

Open ticket = status in `NEW`, `ASSIGNED`, `IN_REPAIR`, `READY`.

## Status rules

`NEW → ASSIGNED → IN_REPAIR → READY → DELIVERED`

`CANCELLED` is allowed from any status except `DELIVERED`.

Any other jump → **409**. Same status twice → **409**.

Assign: only from `NEW`, technician must exist and `active=true`. Inactive technician → **409**. Concurrent assigns use `UPDATE … WHERE status='NEW'` and succeed only if `rowcount = 1`.

Delete customer with open tickets → **409**.

Pincode must resolve to at least one district in `SERVICE_DISTRICTS` (config). Outside area or unknown pin → **422**.

## External API

[India Post pincode lookup](https://api.postalpincode.in/pincode/{pincode}) — no key.

Verified behaviour:

- Valid pin (e.g. `110001`): HTTP **200**, JSON `Status: "Success"`, `PostOffice` list with `District`.
- Unknown pin (e.g. `000000`): still HTTP **200**, JSON `Status: "Error"`, `Message: "No records found"`, `PostOffice: null`.

Do not treat HTTP 200 as “pincode is valid”. Parse the JSON.

**If the pincode API is down on customer create: reject.** Service area is a hard rule. Saving “unverified” would let out-of-area customers into the ticket flow. Cached pins still work. Timeouts → **504**. Down / garbage JSON / unexpected shape → **502**. (Not 503: the error table already maps these cases.)

Retries: 1 initial + up to 2 retries, only on timeout and HTTP 5xx. Never retry 4xx or a parsed `Status: Error`.

## Endpoints

| Method | Path | Success | Notes |
| --- | --- | --- | --- |
| GET | `/health` | 200 | liveness |
| GET | `/docs` | 200 | OpenAPI UI |
| GET | `/serviceability/{pincode}` | 200 | lookup + in-area flag |
| POST | `/customers` | 201 | lookup pin, store district |
| GET | `/customers` | 200 | `limit`, `offset` |
| GET | `/customers/{id}` | 200 | |
| PATCH | `/customers/{id}` | 200 | all fields optional; pin change re-checks area |
| DELETE | `/customers/{id}` | 204 | 409 if open tickets |
| POST | `/technicians` | 201 | |
| GET | `/technicians` | 200 | `limit`, `offset`, optional `active` |
| GET | `/technicians/{id}` | 200 | |
| PATCH | `/technicians/{id}` | 200 | |
| DELETE | `/technicians/{id}` | 204 | 409 if open tickets assigned |
| POST | `/tickets` | 201 | status `NEW` |
| GET | `/tickets` | 200 | filters: `status`, `customer_id`, `technician_id`; pagination |
| GET | `/tickets/{id}` | 200 | |
| PATCH | `/tickets/{id}` | 200 | `device`, `issue`, `quoted_price` only |
| POST | `/tickets/{id}/assign` | 200 | body `{technician_id}`; `NEW → ASSIGNED` |
| POST | `/tickets/{id}/status` | 200 | body `{status}`; transition check |
| POST | `/tickets/{id}/cancel` | 200 | → `CANCELLED` |

Idempotent: GET, PUT, DELETE, PATCH of non-status fields. POST create is not. Status POST is not (repeat jump → 409).

## Error envelope (every error)

```json
{"error": {"code": "NOT_FOUND", "message": "Customer 12 not found", "request_id": "…"}}
```

| Situation | HTTP | `code` |
| --- | --- | --- |
| Bad field / body / validation | 422 | `VALIDATION_ERROR` |
| Pincode outside service area or no records | 422 | `PINCODE_OUT_OF_AREA` / `PINCODE_NOT_FOUND` |
| ID not found | 404 | `NOT_FOUND` |
| Duplicate phone, bad status jump, open tickets, inactive technician, assign race | 409 | `CONFLICT` |
| Pincode API timeout | 504 | `UPSTREAM_TIMEOUT` |
| Pincode API down or garbage | 502 | `UPSTREAM_ERROR` |
| Our bug | 500 | `INTERNAL_ERROR` (generic message only; traceback in logs) |

`X-Request-ID` is accepted or generated; echoed on every response; used in logs.

## HTTP notes (Phase 2)

- Path params: `/customers/{id}`. Query params: `?limit=20&offset=0`.
- **201** create (new resource). **204** delete (no body).
- A bad pin from India Post is **not** a 4xx from them.

## Data notes (Phase 4)

Postgres only (not SQLite). Schema via Alembic, never `create_all` in the app. One `AsyncSession` per request (`yield`); commit on success, rollback on error. Ticket list uses `selectinload` so listing does not N+1.

## Compose vs localhost

In Docker Compose the API container’s `localhost` is itself. Postgres is the `db` service hostname on the compose network. `DATABASE_URL` host is `db`, not `localhost`.

Volume: `docker compose down` keeps the named volume; `down -v` deletes it, so data is gone.
