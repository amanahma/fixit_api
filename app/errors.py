from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.request_context import get_request_id
from app.services.ticket_rules import InvalidTransition


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(404, "NOT_FOUND", message)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "CONFLICT", message)


class PincodeNotFoundError(AppError):
    def __init__(self, pincode: str) -> None:
        super().__init__(422, "PINCODE_NOT_FOUND", f"No postal records for pincode {pincode}")


class PincodeOutOfAreaError(AppError):
    def __init__(self, pincode: str, districts: list[str]) -> None:
        joined = ", ".join(districts) if districts else "unknown"
        super().__init__(
            422,
            "PINCODE_OUT_OF_AREA",
            f"Pincode {pincode} is outside the service area (districts: {joined})",
        )


class PincodeApiTimeoutError(AppError):
    def __init__(self) -> None:
        super().__init__(504, "UPSTREAM_TIMEOUT", "Pincode lookup timed out")


class PincodeApiUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(502, "UPSTREAM_ERROR", "Pincode lookup failed")


def error_body(code: str, message: str) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": get_request_id(),
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(InvalidTransition)
    async def transition_handler(_request: Request, exc: InvalidTransition) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error_body("CONFLICT", str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", _validation_message(exc)),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        message = str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content=error_body(code, message))

    @app.exception_handler(IntegrityError)
    async def integrity_handler(_request: Request, _exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error_body("CONFLICT", "Resource conflicts with an existing value"),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger = getattr(request.app.state, "logger", None)
        if logger is not None:
            logger.exception(
                "unhandled error request_id=%s",
                get_request_id(),
                exc_info=exc,
            )
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "An unexpected error occurred"),
        )


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid request"
    first = errors[0]
    loc = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    msg = first.get("msg", "Invalid value")
    if loc:
        return f"{loc}: {msg}"
    return str(msg)
