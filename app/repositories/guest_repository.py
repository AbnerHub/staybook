from sqlalchemy.orm import Session

from app.models.guest import Guest, IdentificationType


class GuestRepository:
    """Capa de acceso a datos para la entidad Guest."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, guest: Guest) -> Guest:
        """Insertar un nuevo registro de huésped."""
        self.db.add(guest)
        self.db.flush()
        self.db.refresh(guest)
        return guest

    def get_by_id(self, guest_id: int) -> Guest | None:
        """Buscar huésped por ID. Retorna None si no existe."""
        return self.db.get(Guest, guest_id)

    def get_by_email(self, email: str) -> Guest | None:
        """Buscar huésped por email. Retorna None si no existe."""
        return self.db.query(Guest).filter(Guest.email == email).first()

    def get_by_identification(
        self,
        identification_type: IdentificationType,
        identification_number: str,
    ) -> Guest | None:
        """Buscar huésped por documento (tipo + número). Retorna None si no existe."""
        return (
            self.db.query(Guest)
            .filter(
                Guest.identification_type == identification_type,
                Guest.identification_number == identification_number,
            )
            .first()
        )

    def get_all(self) -> list[Guest]:
        """Retornar todos los huéspedes."""
        return self.db.query(Guest).all()

    def update(self, guest: Guest) -> Guest:
        """Persistir cambios en un huésped existente."""
        self.db.flush()
        self.db.refresh(guest)
        return guest
