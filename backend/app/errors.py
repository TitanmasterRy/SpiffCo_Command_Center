"""Application error hierarchy and FastAPI exception handlers.

Every error returned by the API uses one JSON envelope::

    {"error": {"code": "not_found", "message": "...", "details": {...}}}

Services raise :class:`AppError` subclasses; routers never build error
responses by hand.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all expected application errors."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    """A requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ValidationFailedError(AppError):
    """Input was syntactically valid but semantically wrong."""

    status_code = 422
    code = "validation_failed"


class ConflictError(AppError):
    """The request conflicts with current state (e.g. duplicate name)."""

    status_code = 409
    code = "conflict"


class UpstreamUnavailableError(AppError):
    """An upstream dependency (e.g. the FRM mod) is unreachable."""

    status_code = 503
    code = "upstream_unavailable"


class UnauthorizedError(AppError):
    """Authentication is required or the supplied credentials are invalid."""

    status_code = 401
    code = "unauthorized"


def _error_response(status_code: int, code: str, message: str, details: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the standard exception handlers to *app*."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            422, "validation_failed", "Request validation failed", {"errors": exc.errors()}
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(500, "internal_error", "An unexpected error occurred", {})
