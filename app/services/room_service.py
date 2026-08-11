"""Room service — business logic layer for room management."""

from app.core.exceptions import (
    RoomDuplicateException,
    RoomNotFoundException,
    RoomOccupiedException,
)
from app.core.logging import audit_log
from app.models.room import Room, RoomStatus
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomCreate, RoomUpdate


class RoomService:
    """Servicio de habitaciones. Aplica reglas de negocio y coordina operaciones."""

    def __init__(self, repository: RoomRepository):
        self.repository = repository

    def create_room(self, data: RoomCreate) -> Room:
        """
        Crear habitación.

        Reglas:
        - room_number debe ser único
        - status se inicializa como 'disponible' si no se proporciona
        """
        existing = self.repository.get_by_room_number(data.room_number)
        if existing is not None:
            raise RoomDuplicateException()

        room = Room(
            room_number=data.room_number,
            room_type=data.room_type,
            price_per_night=data.price_per_night,
            capacity=data.capacity,
            status=data.status if data.status else RoomStatus.DISPONIBLE,
            description=data.description,
            floor=data.floor,
        )

        created_room = self.repository.create(room)

        try:
            audit_log("create", created_room.id, "success")
        except Exception:
            audit_log("create", created_room.id, "failure")

        return created_room

    def list_rooms(self) -> list[Room]:
        """Retornar todas las habitaciones."""
        return self.repository.get_all()

    def list_available_rooms(self) -> list[Room]:
        """Retornar solo habitaciones con status='disponible'."""
        return self.repository.get_available()

    def get_room(self, room_id: int) -> Room:
        """
        Obtener habitación por ID.

        Lanza RoomNotFoundException si no existe.
        """
        room = self.repository.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundException()
        return room

    def update_room(self, room_id: int, data: RoomUpdate) -> Room:
        """
        Actualización parcial.

        Reglas:
        - La habitación debe existir
        - Si se cambia room_number, no debe existir duplicado
        - Solo se actualizan campos proporcionados (exclude_unset)
        """
        room = self.repository.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundException()

        update_data = data.model_dump(exclude_unset=True)

        if "room_number" in update_data:
            new_room_number = update_data["room_number"]
            if new_room_number != room.room_number:
                existing = self.repository.get_by_room_number(new_room_number)
                if existing is not None:
                    raise RoomDuplicateException()

        for field, value in update_data.items():
            setattr(room, field, value)

        updated_room = self.repository.update(room)

        try:
            audit_log("update", updated_room.id, "success")
        except Exception:
            audit_log("update", updated_room.id, "failure")

        return updated_room

    def delete_room(self, room_id: int) -> None:
        """
        Eliminación permanente (hard delete).

        Reglas:
        - La habitación debe existir
        - No se puede eliminar si status='ocupada'
        - Se permite eliminar si status='mantenimiento' o 'disponible'
        """
        room = self.repository.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundException()

        if room.status == RoomStatus.OCUPADA:
            raise RoomOccupiedException()

        room_id_for_log = room.id
        self.repository.delete(room)

        try:
            audit_log("delete", room_id_for_log, "success")
        except Exception:
            audit_log("delete", room_id_for_log, "failure")
