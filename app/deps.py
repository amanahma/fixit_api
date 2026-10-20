from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db import session_dependency
from app.services.pincode_client import PincodeClient


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory = cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)
    async for session in session_dependency(factory):
        yield session


def get_pincode_client(request: Request) -> PincodeClient:
    return cast(PincodeClient, request.app.state.pincode_client)


DbSession = Annotated[AsyncSession, Depends(get_db)]
PincodeSvc = Annotated[PincodeClient, Depends(get_pincode_client)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
