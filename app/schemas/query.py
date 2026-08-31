"""Schemas for history / occupancy / availability queries (read-only)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.reservation import ReservationStatus
from app.models.room import RoomStatus, RoomType


class OccupancySummaryResponse(BaseModel):
    """Resumen de ocupación actual del hotel."""

    total_rooms: int
    occupied_rooms: int
    available_rooms: int
    maintenance_rooms: int
    occupancy_rate: float


class OccupiedRoomResponse(BaseModel):
    """Habitación actualmente ocupada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_number: str
    room_type: RoomType
    status: RoomStatus


class AvailabilityQuery(BaseModel):
    """Query params para disponibilidad por rango de fechas."""

    check_in_date: date
    check_out_date: date

    @model_validator(mode="after")
    def _check_range(self) -> "AvailabilityQuery":
        if self.check_out_date <= self.check_in_date:
            raise ValueError(
                "check_out_date debe ser posterior a check_in_date"
            )
        return self


class HistoryQuery(BaseModel):
    """Query params para el historial de reservas.

    El filtrado por fecha es both-or-neither: se proporcionan ambas fechas o
    ninguna. Proveer solo una de las dos es un error de validación (422).
    """

    guest_id: int | None = Field(None, gt=0)
    room_id: int | None = Field(None, gt=0)
    status: ReservationStatus | None = None
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def _check_date_range(self) -> "HistoryQuery":
        if (self.date_from is None) != (self.date_to is None):
            raise ValueError(
                "date_from y date_to deben proporcionarse ambos o ninguno"
            )
        if self.date_from is not None and self.date_to <= self.date_from:
            raise ValueError("date_to debe ser posterior a date_from")
        return self
