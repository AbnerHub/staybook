import enum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.db.base import Base


class ReservationStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guest_id = Column(
        Integer, ForeignKey("guests.id"), nullable=False, index=True
    )
    room_id = Column(
        Integer, ForeignKey("rooms.id"), nullable=False, index=True
    )
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    status = Column(
        SAEnum(ReservationStatus),
        nullable=False,
        default=ReservationStatus.CONFIRMED,
        index=True,
    )
    total_price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
