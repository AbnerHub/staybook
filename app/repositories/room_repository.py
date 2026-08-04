from sqlalchemy.orm import Session

from app.models.room import Room, RoomStatus


class RoomRepository:
    """Capa de acceso a datos para la entidad Room."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, room: Room) -> Room:
        """Insertar un nuevo registro de habitación."""
        self.db.add(room)
        self.db.flush()
        self.db.refresh(room)
        return room

    def get_by_id(self, room_id: int) -> Room | None:
        """Buscar habitación por ID. Retorna None si no existe."""
        return self.db.get(Room, room_id)

    def get_by_room_number(self, room_number: str) -> Room | None:
        """Buscar habitación por número. Retorna None si no existe."""
        return (
            self.db.query(Room)
            .filter(Room.room_number == room_number)
            .first()
        )

    def get_all(self) -> list[Room]:
        """Retornar todas las habitaciones."""
        return self.db.query(Room).all()

    def get_available(self) -> list[Room]:
        """Retornar habitaciones con status='disponible'."""
        return (
            self.db.query(Room)
            .filter(Room.status == RoomStatus.DISPONIBLE)
            .all()
        )

    def update(self, room: Room) -> Room:
        """Persistir cambios en una habitación existente."""
        self.db.flush()
        self.db.refresh(room)
        return room

    def delete(self, room: Room) -> None:
        """Eliminar físicamente el registro de la habitación."""
        self.db.delete(room)
        self.db.flush()
