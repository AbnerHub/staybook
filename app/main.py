"""StayBook application entry point."""

from fastapi import FastAPI

from app.api.guests import router as guests_router
from app.api.reservations import router as reservations_router
from app.api.rooms import router as rooms_router
from app.core.exception_handlers import (
    app_exception_handler,
    generic_exception_handler,
)
from app.core.exceptions import AppException

app = FastAPI(title="StayBook", version="1.0.0")

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(rooms_router)
app.include_router(guests_router)
app.include_router(reservations_router)
