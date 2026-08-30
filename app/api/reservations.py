"""Reservation management API router — presentation layer."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user
from app.db.session import get_db
from app.repositories.guest_repository import GuestRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.reservation import (
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
)
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/api/v1/reservations", tags=["reservations"])


def _get_service(db: Session = Depends(get_db)) -> ReservationService:
    """Build the service with its repository dependencies (reusing Room/Guest)."""
    return ReservationService(
        repository=ReservationRepository(db),
        room_repository=RoomRepository(db),
        guest_repository=GuestRepository(db),
    )


@router.post(
    "/", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED
)
def create_reservation(
    reservation_data: ReservationCreate,
    current_user: dict = Depends(get_current_admin_user),
    service: ReservationService = Depends(_get_service),
) -> ReservationResponse:
    """Crear una nueva reserva."""
    reservation = service.create_reservation(reservation_data)
    return ReservationResponse.model_validate(reservation)


@router.get("/", response_model=list[ReservationResponse])
def list_reservations(
    current_user: dict = Depends(get_current_admin_user),
    service: ReservationService = Depends(_get_service),
) -> list[ReservationResponse]:
    """Listar todas las reservas (confirmed y cancelled)."""
    reservations = service.list_reservations()
    return [ReservationResponse.model_validate(r) for r in reservations]


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(
    reservation_id: int,
    current_user: dict = Depends(get_current_admin_user),
    service: ReservationService = Depends(_get_service),
) -> ReservationResponse:
    """Obtener detalle de una reserva por ID."""
    reservation = service.get_reservation(reservation_id)
    return ReservationResponse.model_validate(reservation)


@router.patch("/{reservation_id}", response_model=ReservationResponse)
def update_reservation(
    reservation_id: int,
    reservation_data: ReservationUpdate,
    current_user: dict = Depends(get_current_admin_user),
    service: ReservationService = Depends(_get_service),
) -> ReservationResponse:
    """Actualizar parcialmente una reserva (room_id / fechas)."""
    reservation = service.update_reservation(reservation_id, reservation_data)
    return ReservationResponse.model_validate(reservation)


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_reservation(
    reservation_id: int,
    current_user: dict = Depends(get_current_admin_user),
    service: ReservationService = Depends(_get_service),
) -> ReservationResponse:
    """Cancelar una reserva (cambio de estado, sin borrado físico)."""
    reservation = service.cancel_reservation(reservation_id)
    return ReservationResponse.model_validate(reservation)
