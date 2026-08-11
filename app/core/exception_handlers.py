"""Global exception handlers for the StayBook application."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler global para excepciones de dominio."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler para excepciones no controladas — no expone detalles internos."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "status_code": 500},
    )
