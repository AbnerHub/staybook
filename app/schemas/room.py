from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.room import RoomStatus, RoomType


class RoomCreate(BaseModel):
    room_number: str = Field(
        ..., max_length=10, description="Número de habitación"
    )
    room_type: RoomType
    price_per_night: float = Field(..., gt=0, le=999999.99)
    capacity: int = Field(..., ge=1, le=20)
    status: RoomStatus = RoomStatus.DISPONIBLE
    description: str | None = Field(None, max_length=255)
    floor: int | None = None


class RoomUpdate(BaseModel):
    room_number: str | None = Field(None, max_length=10)
    room_type: RoomType | None = None
    price_per_night: float | None = Field(None, gt=0, le=999999.99)
    capacity: int | None = Field(None, ge=1, le=20)
    status: RoomStatus | None = None
    description: str | None = Field(None, max_length=255)
    floor: int | None = None


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_number: str
    room_type: RoomType
    price_per_night: float
    capacity: int
    status: RoomStatus
    description: str | None
    floor: int | None
    created_at: datetime
    updated_at: datetime
