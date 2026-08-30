import enum

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func

from app.db.base import Base


class IdentificationType(str, enum.Enum):
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    OTHER = "other"


class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    identification_type = Column(SAEnum(IdentificationType), nullable=False)
    identification_number = Column(String(50), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "identification_type",
            "identification_number",
            name="uq_guests_identification",
        ),
    )
