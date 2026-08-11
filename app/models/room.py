import enum

from sqlalchemy import Column, Integer, Numeric, String, DateTime, Enum as SAEnum
from sqlalchemy.sql import func

from app.db.base import Base


class RoomType(str, enum.Enum):
    INDIVIDUAL = "individual"
    DOBLE = "doble"
    SUITE = "suite"


class RoomStatus(str, enum.Enum):
    DISPONIBLE = "disponible"
    OCUPADA = "ocupada"
    MANTENIMIENTO = "mantenimiento"


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_number = Column(String(10), unique=True, nullable=False, index=True)
    room_type = Column(SAEnum(RoomType), nullable=False)
    price_per_night = Column(Numeric(8, 2), nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(
        SAEnum(RoomStatus), nullable=False, default=RoomStatus.DISPONIBLE
    )
    description = Column(String(255), nullable=True)
    floor = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
