from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.guest import IdentificationType


def _strip_and_require_non_empty(value: str | None) -> str | None:
    """Recorta espacios y rechaza cadenas vacías tras el recorte."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("El campo no puede estar vacío ni contener solo espacios")
    return stripped


class GuestCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr = Field(..., max_length=255)
    phone: str = Field(..., min_length=7, max_length=20)
    identification_type: IdentificationType
    identification_number: str = Field(..., min_length=1, max_length=50)

    @field_validator("first_name", "last_name", "identification_number")
    @classmethod
    def _no_whitespace_only(cls, value: str) -> str:
        return _strip_and_require_non_empty(value)


class GuestUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = Field(None, max_length=255)
    phone: str | None = Field(None, min_length=7, max_length=20)
    identification_type: IdentificationType | None = None
    identification_number: str | None = Field(None, min_length=1, max_length=50)

    @field_validator("first_name", "last_name", "identification_number")
    @classmethod
    def _no_whitespace_only(cls, value: str | None) -> str | None:
        return _strip_and_require_non_empty(value)


class GuestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    identification_type: IdentificationType
    identification_number: str
    created_at: datetime
    updated_at: datetime
