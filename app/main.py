from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings, get_settings
from app.db import create_engine, create_session_factory
from app.errors import register_error_handlers
from app.logging_setup import configure_logging, install_request_logging
from app.routers import customers, serviceability, technicians, tickets
from app.schemas import HealthRead
from app.services.pincode_client import PincodeClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine: AsyncEngine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    http = httpx.AsyncClient()
    app.state.http_client = http
    app.state.pincode_client = PincodeClient(
        http=http,
        base_url=settings.pincode_api_base_url,
        timeout_seconds=settings.http_timeout_seconds,
        max_retries=settings.pincode_max_retries,
        service_districts=settings.districts,
    )
    try:
        yield
    finally:
        await http.aclose()
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    logger = configure_logging(resolved.log_level)
    app = FastAPI(
        title="Fixit API",
        description="Repair-ticket service (learning project, not a product launch).",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.logger = logger
    install_request_logging(app, logger)
    register_error_handlers(app)
    app.include_router(customers.router)
    app.include_router(technicians.router)
    app.include_router(tickets.router)
    app.include_router(serviceability.router)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.get("/health", response_model=HealthRead, tags=["health"])
    async def health() -> HealthRead:
        return HealthRead(status="ok")

    if resolved.enable_error_probe:

        @app.get("/debug/boom", tags=["health"], include_in_schema=False)
        async def boom() -> None:
            raise RuntimeError("intentional probe")

    return app
