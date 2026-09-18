"""Exceptions applicatives et gestionnaires d'erreurs FastAPI.

Une erreur porte une **cle de message**, pas une phrase. La phrase n'est
choisie qu'au moment de repondre, quand la langue de l'appelant est connue :
c'est le seul endroit ou elle le soit vraiment, un service ne sachant rien de
la requete qui l'a declenche.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.i18n import request_locale, translate

logger = logging.getLogger("filmfund.errors")


class AppError(Exception):
    """Erreur metier avec code HTTP explicite.

    `key` designe une entree des catalogues (`app/core/i18n.py`) ; `params`
    remplit ses variables. Le texte lui-meme n'est produit qu'a la reponse.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(
        self,
        key: str,
        *,
        params: dict[str, Any] | None = None,
        status_code: int | None = None,
        code: str | None = None,
    ):
        self.key = key
        self.params = params or {}
        # `str(exc)` sert aux journaux et aux traces : la langue de reference
        # y est plus utile que celle de l'appelant.
        super().__init__(self.detail)
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code

    @property
    def detail(self) -> str:
        """Message dans la langue de reference, pour les journaux."""
        return translate("fr", self.key, **self.params)

    def localized(self, locale: str) -> str:
        return translate(locale, self.key, **self.params)  # type: ignore[arg-type]


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
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.localized(request_locale(request)), "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Les messages par champ viennent de Pydantic et restent en anglais :
        # les retraduire supposerait de rejouer sa logique de validation.
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": translate(request_locale(request), "error.validation"),
                "code": "validation_error",
                "errors": [
                    {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]}
                    for err in exc.errors()
                ],
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Erreur base de données", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": translate(request_locale(request), "error.database"),
                "code": "database_error",
            },
        )
