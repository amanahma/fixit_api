from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    PincodeApiTimeoutError,
    PincodeApiUnavailableError,
    PincodeNotFoundError,
    PincodeOutOfAreaError,
)
from app.models import PincodeCache

logger = logging.getLogger(__name__)


class PincodeClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        service_districts: frozenset[str],
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._service_districts = service_districts

    async def lookup_districts(self, session: AsyncSession, pincode: str) -> list[str]:
        cached = await session.scalar(select(PincodeCache).where(PincodeCache.pincode == pincode))
        if cached is not None:
            return list(cached.districts)

        districts = await self._fetch_districts(pincode)
        session.add(
            PincodeCache(pincode=pincode, districts=districts, fetched_at=datetime.now(UTC))
        )
        await session.flush()
        return districts

    async def require_serviceable(self, session: AsyncSession, pincode: str) -> str:
        districts = await self.lookup_districts(session, pincode)
        matched = next((d for d in districts if d in self._service_districts), None)
        if matched is None:
            raise PincodeOutOfAreaError(pincode, districts)
        return matched

    async def serviceability(
        self, session: AsyncSession, pincode: str
    ) -> tuple[list[str], bool, str | None]:
        districts = await self.lookup_districts(session, pincode)
        matched = next((d for d in districts if d in self._service_districts), None)
        return districts, matched is not None, matched

    async def _fetch_districts(self, pincode: str) -> list[str]:
        url = f"{self._base_url}/pincode/{pincode}"
        payload = await self._get_json(url)
        return _districts_from_payload(pincode, payload)

    async def _get_json(self, url: str) -> Any:
        attempts = self._max_retries + 1
        last_timeout = False
        for attempt in range(attempts):
            try:
                response = await self._http.get(url, timeout=self._timeout)
            except httpx.TimeoutException:
                last_timeout = True
                logger.warning("pincode api timeout attempt=%s url=%s", attempt + 1, url)
                if attempt == attempts - 1:
                    raise PincodeApiTimeoutError from None
                continue
            except httpx.HTTPError:
                last_timeout = False
                logger.warning("pincode api connection error attempt=%s url=%s", attempt + 1, url)
                if attempt == attempts - 1:
                    raise PincodeApiUnavailableError from None
                continue

            if response.status_code >= 500:
                last_timeout = False
                logger.warning(
                    "pincode api 5xx status=%s attempt=%s", response.status_code, attempt + 1
                )
                if attempt == attempts - 1:
                    raise PincodeApiUnavailableError
                continue

            if response.status_code >= 400:
                raise PincodeApiUnavailableError

            try:
                return response.json()
            except json.JSONDecodeError as exc:
                raise PincodeApiUnavailableError from exc
            except ValueError as exc:
                raise PincodeApiUnavailableError from exc

        if last_timeout:
            raise PincodeApiTimeoutError
        raise PincodeApiUnavailableError


def _districts_from_payload(pincode: str, payload: Any) -> list[str]:
    if not isinstance(payload, list) or not payload:
        raise PincodeApiUnavailableError
    first = payload[0]
    if not isinstance(first, dict):
        raise PincodeApiUnavailableError

    status = first.get("Status")
    offices = first.get("PostOffice")
    if status == "Error" or offices is None:
        raise PincodeNotFoundError(pincode)
    if status != "Success" or not isinstance(offices, list):
        raise PincodeApiUnavailableError

    districts: list[str] = []
    seen: set[str] = set()
    for office in offices:
        if not isinstance(office, dict):
            continue
        district = office.get("District")
        if isinstance(district, str) and district and district not in seen:
            seen.add(district)
            districts.append(district)
    if not districts:
        raise PincodeApiUnavailableError
    return districts
