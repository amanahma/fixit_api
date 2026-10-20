# AI failure write-up

Not staged. Caught against a live response from the pincode API, then against the error table in DESIGN.md.

## What was proposed

A customer-create path that mapped “pincode API failed” to **503**, and treated a non-2xx (or empty) HTTP status as the way to detect a bad pincode.

## Why it was wrong

1. **India Post hides errors in JSON.** `GET https://api.postalpincode.in/pincode/000000` returns HTTP 200 with `{"Status":"Error","Message":"No records found","PostOffice":null}`. Mapping only HTTP status would have stored or 500’d on an unknown pin. Verified with a live fetch of `110001` (Success + District list) and `000000` (Error).
2. **The error table already assigned 502/504** for upstream timeout / down / garbage. Using 503 would have two codes for the same situation and would confuse the smoke test and reviewers.
3. **“Save as unverified”** would skip the service-area rule. Tickets could then be created for customers outside `SERVICE_DISTRICTS`.

## How it was caught

Reading the raw JSON (Phase 2 requirement) instead of assuming REST-ish 4xx from a free API. Then matching DESIGN.md’s table: timeout 504, down/garbage 502, no records / out of area 422.

## What changed

`PincodeClient` parses `Status` and `PostOffice`. No records → 422 `PINCODE_NOT_FOUND`. Out of area → 422 `PINCODE_OUT_OF_AREA`. Timeouts retry then 504. 5xx, connect errors, and broken JSON retry then 502. Successful lookups go in `pincode_cache` so a later outage does not block known pins.

## Second miss (local Postgres)

SQLAlchemy 2.0’s `str(make_url(...))` **redacts the password to `***`**. `normalize_database_url` returned that string, so asyncpg authenticated as `fixit` / `***` and raised `InvalidPasswordError`. Direct `asyncpg.connect(password="fixit")` worked, which made it look like Docker or SSL. Fix: `url.render_as_string(hide_password=False)`. Also publish Compose on host port **5433** because native PostgreSQL 18 already owns 5432.

## Lesson

The status line is not the contract. For a public API, write one test per *actual* body shape (`Success`, `Error` + null offices, 500, timeout, non-JSON) with respx, and never call the network from pytest.

Never pass `str(sqlalchemy_url)` into a connector: SQLAlchemy 2 hides the password. Compare a failing ORM connect with a raw `asyncpg.connect` using an explicit password before blaming Docker or TLS.
