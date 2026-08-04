"""Room management API router — presentation layer."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user
from app.db.session import get_db
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate
from app.services.room_service import RoomService

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


def _get_service(db: Session = Depends(get_db)) -> RoomService:
    """Build the service with its repository dependency."""
    repository = RoomRepository(db)
    return RoomService(repository)


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    room_data: RoomCreate,
    current_user: dict = Depends(get_current_admin_user),
    service: RoomService = Depends(_get_service),
) -> RoomResponse:
    """Registrar una nueva habitación."""
    room = service.create_room(room_data)
    return RoomResponse.model_validate(room)


@router.get("/", response_model=list[RoomResponse])
def list_rooms(
    current_user: dict = Depends(get_current_admin_user),
    service: RoomService = Depends(_get_service),
) -> list[RoomResponse]:
    """Listar todas las habitaciones."""
    rooms = service.list_rooms()
    return [RoomResponse.model_validate(r) for r in rooms]


@router.get("/available", response_model=list[RoomResponse])
def list_available_rooms(
    current_user: dict = Depends(get_current_admin_user),
    service: RoomService = Depends(_get_service),
) -> list[RoomResponse]:
    """Listar habitaciones disponibles."""
    rooms = service.list_available_rooms()
    return [RoomResponse.model_validate(r) for r in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(
    room_id: int,
    current_user: dict = Depends(get_current_admin_user),
    service: RoomService = Depends(_get_service),
) -> RoomResponse:
    """Obtener detalle de una habitación por ID."""
    room = service.get_room(room_id)
    return RoomResponse.model_validate(room)


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    room_data: RoomUpdate,
    current_user: dict = Depends(get_current_admin_user),
    service: RoomService = Depends(_get_service),
) -> RoomResponse:
    """Actualizar parcialmente una habitación."""
    room = service.update_room(room_id, room_data)
    return RoomResponse.model_validate(room)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    current_user: dict = Depends(get_current_admin_user),
    service: RoomService = Depends(_get_service),
) -> None:
    """Eliminar una habitación (hard delete)."""
    service.delete_room(room_id)
