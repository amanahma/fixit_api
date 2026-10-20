from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.request_context import request_id_ctx

PHONE_RE = re.compile(r"\b([6-9]\d{1})\d{6}(\d{2})\b")


class PhoneMaskFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_phones(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: mask_phones(str(v)) for k, v in record.args.items()}
            else:
                record.args = tuple(mask_phones(str(arg)) for arg in record.args)
        return True


def mask_phones(value: str) -> str:
    return PHONE_RE.sub(r"\1xxxxxx\2", value)


def configure_logging(level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    logger = logging.getLogger("fixit")
    mask = PhoneMaskFilter()
    logger.addFilter(mask)
    logging.getLogger().addFilter(mask)
    return logger


def install_request_logging(app: FastAPI, logger: logging.Logger) -> None:
    @app.middleware("http")
    async def request_logger(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "request_id=%s method=%s path=%s status=500 duration_ms=%s",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        else:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%s",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)
