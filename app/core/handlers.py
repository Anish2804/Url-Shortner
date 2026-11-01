"""Centralized FastAPI exception handlers ensuring standard response envelopes."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger("exception_handlers")


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Application exception: %s (code=%s)",
            exc.message,
            exc.code,
            extra={"extra_fields": {"path": request.url.path, "code": exc.code, "status_code": exc.status_code}},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for err in exc.errors():
            loc = " -> ".join(str(part) for part in err.get("loc", []))
            errors.append({
                "field": loc,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            })
        logger.info(
            "Request validation failed on %s: %s",
            request.url.path,
            errors,
            extra={"extra_fields": {"path": request.url.path, "errors": errors}},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed. Please check the provided fields.",
                    "details": {"validation_errors": errors},
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.info("HTTP exception: %s status=%d", exc.detail, exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "details": {},
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled server error on %s: %s",
            request.url.path,
            str(exc),
            extra={"extra_fields": {"path": request.url.path}},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred. Please try again later.",
                    "details": {},
                },
            },
        )
