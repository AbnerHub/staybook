from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.reservation import ReservationStatus


class ReservationCreate(BaseModel):
    # extra="forbid": si el cliente envía total_price, status u otro campo
    # gestionado por el servidor, Pydantic rechaza con 422.
    model_config = ConfigDict(extra="forbid")

    guest_id: int = Field(..., gt=0)
    room_id: int = Field(..., gt=0)
    check_in_date: date
    check_out_date: date

    @model_validator(mode="after")
    def _check_dates(self) -> "ReservationCreate":
        if self.check_out_date <= self.check_in_date:
            raise ValueError(
                "check_out_date debe ser posterior a check_in_date"
            )
        return self


class ReservationUpdate(BaseModel):
    # extra="forbid": rechaza campos gestionados por el servidor (total_price,
    # status, etc.) con 422. La validación de fechas del estado resultante se
    # realiza en el servicio, ya que un update parcial puede traer solo una fecha.
    model_config = ConfigDict(extra="forbid")

    room_id: int | None = Field(None, gt=0)
    check_in_date: date | None = None
    check_out_date: date | None = None


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    guest_id: int
    room_id: int
    check_in_date: date
    check_out_date: date
    status: ReservationStatus
    total_price: Decimal
    created_at: datetime
    updated_at: datetime
