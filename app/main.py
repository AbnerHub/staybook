"""StayBook application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.guests import router as guests_router
from app.api.queries import router as queries_router
from app.api.reservations import router as reservations_router
from app.api.rooms import router as rooms_router
from app.core.config import settings
from app.core.exception_handlers import (
    app_exception_handler,
    generic_exception_handler,
)
from app.core.exceptions import AppException

app = FastAPI(title="StayBook", version="1.0.0")

# CORS: allow the frontend dev origin to call the API from the browser.
# Origins are configurable via the CORS_ORIGINS environment variable
# (comma-separated); "*" is intentionally avoided to stay compatible with
# credentials and the Authorization header.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(rooms_router)
app.include_router(guests_router)
app.include_router(reservations_router)
app.include_router(queries_router)
