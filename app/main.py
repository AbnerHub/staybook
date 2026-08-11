"""StayBook application entry point."""

from fastapi import FastAPI

from app.api.rooms import router
from app.core.exception_handlers import (
    app_exception_handler,
    generic_exception_handler,
)
from app.core.exceptions import AppException

app = FastAPI(title="StayBook", version="1.0.0")

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(router)
