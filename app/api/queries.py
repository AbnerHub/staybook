"""History / occupancy / availability query API router — read-only."""

from datetime import date

from fastapi import APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user
from app.db.session import get_db
from app.models.reservation import ReservationStatus
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.query import (
    AvailabilityQuery,
    HistoryQuery,
    OccupancySummaryResponse,
    OccupiedRoomResponse,
)
from app.schemas.reservation import ReservationResponse
from app.schemas.room import RoomResponse
from app.services.query_service import HistoryFilters, QueryService

router = APIRouter(prefix="/api/v1", tags=["queries"])


def _get_query_service(db: Session = Depends(get_db)) -> QueryService:
    """Build the read-only query service reusing existing repositories."""
    return QueryService(
        room_repository=RoomRepository(db),
        reservation_repository=ReservationRepository(db),
    )


def _availability_params(
    check_in_date: date,
    check_out_date: date,
) -> AvailabilityQuery:
    """Validate availability query params → 422 on cross-field errors."""
    try:
        return AvailabilityQuery(
            check_in_date=check_in_date, check_out_date=check_out_date
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


def _history_params(
    guest_id: int | None = None,
    room_id: int | None = None,
    status: ReservationStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> HistoryQuery:
    """Validate history query params → 422 on cross-field errors."""
    try:
        return HistoryQuery(
            guest_id=guest_id,
            room_id=room_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


@router.get("/occupancy/current", response_model=OccupancySummaryResponse)
def get_current_occupancy(
    current_user: dict = Depends(get_current_admin_user),
    service: QueryService = Depends(_get_query_service),
) -> OccupancySummaryResponse:
    """Resumen de ocupación actual del hotel."""
    summary = service.get_current_occupancy()
    return OccupancySummaryResponse(
        total_rooms=summary.total_rooms,
        occupied_rooms=summary.occupied_rooms,
        available_rooms=summary.available_rooms,
        maintenance_rooms=summary.maintenance_rooms,
        occupancy_rate=summary.occupancy_rate,
    )


@router.get("/occupancy/rooms", response_model=list[OccupiedRoomResponse])
def list_occupied_rooms(
    current_user: dict = Depends(get_current_admin_user),
    service: QueryService = Depends(_get_query_service),
) -> list[OccupiedRoomResponse]:
    """Listar las habitaciones actualmente ocupadas."""
    rooms = service.list_occupied_rooms()
    return [OccupiedRoomResponse.model_validate(r) for r in rooms]


@router.get("/availability", response_model=list[RoomResponse])
def list_available_rooms(
    query: AvailabilityQuery = Depends(_availability_params),
    current_user: dict = Depends(get_current_admin_user),
    service: QueryService = Depends(_get_query_service),
) -> list[RoomResponse]:
    """Listar las habitaciones disponibles para un rango de fechas."""
    rooms = service.list_available_rooms(query.check_in_date, query.check_out_date)
    return [RoomResponse.model_validate(r) for r in rooms]


@router.get("/history/reservations", response_model=list[ReservationResponse])
def get_reservation_history(
    query: HistoryQuery = Depends(_history_params),
    current_user: dict = Depends(get_current_admin_user),
    service: QueryService = Depends(_get_query_service),
) -> list[ReservationResponse]:
    """Consultar el historial de reservas con filtros opcionales."""
    reservations = service.get_reservation_history(
        HistoryFilters(
            guest_id=query.guest_id,
            room_id=query.room_id,
            status=query.status,
            date_from=query.date_from,
            date_to=query.date_to,
        )
    )
    return [ReservationResponse.model_validate(r) for r in reservations]
