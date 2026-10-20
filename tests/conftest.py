from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import pytest_asyncio
import respx
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Prefer TEST_DATABASE_URL. Locally do not inherit a developer DATABASE_URL
# (native Postgres on 5432, Neon + ssl, etc.). CI keeps DATABASE_URL.
if "TEST_DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
elif not os.environ.get("CI"):
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://fixit:fixit@127.0.0.1:5433/fixit_test"
os.environ.setdefault(
    "SERVICE_DISTRICTS",
    "New Delhi,Central Delhi,South Delhi,North Delhi,East Delhi,West Delhi",
)
os.environ.setdefault("PINCODE_API_BASE_URL", "https://api.postalpincode.in")
os.environ.setdefault("HTTP_TIMEOUT_SECONDS", "5")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ENABLE_ERROR_PROBE", "true")

from app.config import Settings, reset_settings_cache  # noqa: E402
from app.db import create_engine  # noqa: E402
from app.main import create_app  # noqa: E402

SUCCESS_BODY = [
    {
        "Message": "Number of pincode(s) found:1",
        "Status": "Success",
        "PostOffice": [{"District": "New Delhi", "Name": "New Delhi"}],
    }
]
OUT_OF_AREA_BODY = [
    {
        "Message": "Number of pincode(s) found:1",
        "Status": "Success",
        "PostOffice": [{"District": "Bengaluru Urban", "Name": "Bangalore GPO"}],
    }
]
NO_RECORDS_BODY = [{"Message": "No records found", "Status": "Error", "PostOffice": None}]


@pytest.fixture(scope="session")
def settings() -> Settings:
    reset_settings_cache()
    return Settings()  # type: ignore[call-arg]


@pytest.fixture(scope="session")
def apply_migrations(settings: Settings) -> None:
    async def reset_schema() -> None:
        engine = create_engine(settings)
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(reset_schema())
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture
async def fastapi_app(settings: Settings, apply_migrations: None) -> AsyncIterator[object]:
    application = create_app(settings)
    async with LifespanManager(application):
        yield application
        engine = application.state.engine  # type: ignore[attr-defined]
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE tickets, customers, technicians, pincode_cache "
                    "RESTART IDENTITY CASCADE"
                )
            )


@pytest_asyncio.fixture
async def engine(fastapi_app: object) -> AsyncEngine:
    return fastapi_app.state.engine  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def mock_pincode_api() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        router.get("https://api.postalpincode.in/pincode/110001").mock(
            return_value=httpx.Response(200, json=SUCCESS_BODY)
        )
        router.get("https://api.postalpincode.in/pincode/560001").mock(
            return_value=httpx.Response(200, json=OUT_OF_AREA_BODY)
        )
        router.get("https://api.postalpincode.in/pincode/000000").mock(
            return_value=httpx.Response(200, json=NO_RECORDS_BODY)
        )
        yield router


@pytest_asyncio.fixture
async def client(fastapi_app: object) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
