from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


def normalize_database_url(raw: str) -> tuple[str, dict[str, Any]]:
    """asyncpg does not accept libpq query flags such as sslmode=require (Neon)."""
    url = make_url(raw)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")

    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    query.pop("ssl", None)
    url = url.set(query=query)

    connect_args: dict[str, Any] = {}
    if sslmode in {"require", "verify-ca", "verify-full"}:
        # Neon and other hosted Postgres.
        connect_args["ssl"] = True
    else:
        # asyncpg on Windows defaults to sslmode=prefer, which breaks
        # local Docker Postgres (no TLS) with InvalidPasswordError.
        connect_args["ssl"] = False
    return url.render_as_string(hide_password=False), connect_args


def create_engine(settings: Settings) -> AsyncEngine:
    url, connect_args = normalize_database_url(settings.database_url)
    return create_async_engine(
        url,
        echo=settings.sql_echo,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session_dependency(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
