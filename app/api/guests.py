"""Guest management API router — presentation layer."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user
from app.db.session import get_db
from app.repositories.guest_repository import GuestRepository
from app.schemas.guest import GuestCreate, GuestResponse, GuestUpdate
from app.services.guest_service import GuestService

router = APIRouter(prefix="/api/v1/guests", tags=["guests"])


def _get_service(db: Session = Depends(get_db)) -> GuestService:
    """Build the service with its repository dependency."""
    repository = GuestRepository(db)
    return GuestService(repository)


@router.post("/", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
def create_guest(
    guest_data: GuestCreate,
    current_user: dict = Depends(get_current_admin_user),
    service: GuestService = Depends(_get_service),
) -> GuestResponse:
    """Registrar un nuevo huésped."""
    guest = service.create_guest(guest_data)
    return GuestResponse.model_validate(guest)


@router.get("/", response_model=list[GuestResponse])
def list_guests(
    current_user: dict = Depends(get_current_admin_user),
    service: GuestService = Depends(_get_service),
) -> list[GuestResponse]:
    """Listar todos los huéspedes."""
    guests = service.list_guests()
    return [GuestResponse.model_validate(g) for g in guests]


@router.get("/{guest_id}", response_model=GuestResponse)
def get_guest(
    guest_id: int,
    current_user: dict = Depends(get_current_admin_user),
    service: GuestService = Depends(_get_service),
) -> GuestResponse:
    """Obtener detalle de un huésped por ID."""
    guest = service.get_guest(guest_id)
    return GuestResponse.model_validate(guest)


@router.patch("/{guest_id}", response_model=GuestResponse)
def update_guest(
    guest_id: int,
    guest_data: GuestUpdate,
    current_user: dict = Depends(get_current_admin_user),
    service: GuestService = Depends(_get_service),
) -> GuestResponse:
    """Actualizar parcialmente un huésped."""
    guest = service.update_guest(guest_id, guest_data)
    return GuestResponse.model_validate(guest)
