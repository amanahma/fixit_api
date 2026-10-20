from __future__ import annotations

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.errors import (
    PincodeApiTimeoutError,
    PincodeApiUnavailableError,
    PincodeNotFoundError,
)
from app.services.pincode_client import PincodeClient
from tests.conftest import NO_RECORDS_BODY


def _client() -> PincodeClient:
    return PincodeClient(
        http=httpx.AsyncClient(),
        base_url="https://api.postalpincode.in",
        timeout_seconds=5.0,
        max_retries=2,
        service_districts=frozenset({"New Delhi"}),
    )


@pytest.mark.asyncio
async def test_success_and_cache(engine: object, mock_pincode_api: object) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]
    client = _client()
    async with factory() as session:
        districts = await client.lookup_districts(session, "110001")
        assert districts == ["New Delhi"]
        await session.commit()
    mock_pincode_api.reset()  # type: ignore[union-attr]
    async with factory() as session:
        districts = await client.lookup_districts(session, "110001")
        assert districts == ["New Delhi"]
        await session.commit()
    await client._http.aclose()


@pytest.mark.asyncio
async def test_no_records(mock_pincode_api: object, engine: object) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]
    client = _client()
    async with factory() as session:
        with pytest.raises(PincodeNotFoundError):
            await client.lookup_districts(session, "000000")
    await client._http.aclose()
    assert NO_RECORDS_BODY[0]["Status"] == "Error"


@pytest.mark.asyncio
async def test_timeout(mock_pincode_api: object) -> None:
    mock_pincode_api.get("https://api.postalpincode.in/pincode/110001").mock(  # type: ignore[union-attr]
        side_effect=httpx.TimeoutException("slow")
    )
    client = _client()
    with pytest.raises(PincodeApiTimeoutError):
        await client._fetch_districts("110001")
    await client._http.aclose()


@pytest.mark.asyncio
async def test_upstream_500(mock_pincode_api: object) -> None:
    mock_pincode_api.get("https://api.postalpincode.in/pincode/110001").mock(  # type: ignore[union-attr]
        return_value=httpx.Response(500, text="nope")
    )
    client = _client()
    with pytest.raises(PincodeApiUnavailableError):
        await client._fetch_districts("110001")
    await client._http.aclose()


@pytest.mark.asyncio
async def test_broken_json(mock_pincode_api: object) -> None:
    mock_pincode_api.get("https://api.postalpincode.in/pincode/110001").mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, text="not-json")
    )
    client = _client()
    with pytest.raises(PincodeApiUnavailableError):
        await client._fetch_districts("110001")
    await client._http.aclose()


@pytest.mark.asyncio
async def test_does_not_retry_parsed_error(mock_pincode_api: object, engine: object) -> None:
    route = mock_pincode_api.get("https://api.postalpincode.in/pincode/000000")  # type: ignore[union-attr]
    route.mock(return_value=httpx.Response(200, json=NO_RECORDS_BODY))
    factory = async_sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]
    client = _client()
    async with factory() as session:
        with pytest.raises(PincodeNotFoundError):
            await client.lookup_districts(session, "000000")
    assert route.call_count == 1
    await client._http.aclose()
