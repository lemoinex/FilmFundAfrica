"""Exceptions applicatives et gestionnaires d'erreurs FastAPI."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("filmfund.errors")


class AppError(Exception):
    """Erreur metier avec code HTTP explicite."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(self, detail: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_failed"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class QuotaExceededError(AppError):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    code = "quota_exceeded"


class AIProviderError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ai_provider_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Données invalides.",
                "code": "validation_error",
                "errors": [
                    {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]}
                    for err in exc.errors()
                ],
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Erreur base de données", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erreur interne côté base de données.", "code": "database_error"},
        )
