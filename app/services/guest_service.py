"""Guest service — business logic layer for guest management."""

from app.core.exceptions import (
    GuestEmailDuplicateException,
    GuestIdentificationDuplicateException,
    GuestNotFoundException,
)
from app.core.logging import audit_log
from app.models.guest import Guest
from app.repositories.guest_repository import GuestRepository
from app.schemas.guest import GuestCreate, GuestUpdate


class GuestService:
    """Servicio de huéspedes. Aplica reglas de negocio y coordina operaciones."""

    def __init__(self, repository: GuestRepository):
        self.repository = repository

    def create_guest(self, data: GuestCreate) -> Guest:
        """
        Crear huésped.

        Reglas:
        - email debe ser único
        - (identification_type, identification_number) debe ser único
        """
        if self.repository.get_by_email(data.email) is not None:
            raise GuestEmailDuplicateException()

        if (
            self.repository.get_by_identification(
                data.identification_type, data.identification_number
            )
            is not None
        ):
            raise GuestIdentificationDuplicateException()

        guest = Guest(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            identification_type=data.identification_type,
            identification_number=data.identification_number,
        )

        created_guest = self.repository.create(guest)

        try:
            audit_log("create", created_guest.id, "success")
        except Exception:
            audit_log("create", created_guest.id, "failure")

        return created_guest

    def list_guests(self) -> list[Guest]:
        """Retornar todos los huéspedes."""
        return self.repository.get_all()

    def get_guest(self, guest_id: int) -> Guest:
        """
        Obtener huésped por ID.

        Lanza GuestNotFoundException si no existe.
        """
        guest = self.repository.get_by_id(guest_id)
        if guest is None:
            raise GuestNotFoundException()
        return guest

    def update_guest(self, guest_id: int, data: GuestUpdate) -> Guest:
        """
        Actualización parcial.

        Reglas:
        - El huésped debe existir
        - Si cambia email y ya existe en otro huésped → duplicado
        - Si cambia el documento (tipo + número) y ya existe en otro
          huésped → duplicado
        - Solo se actualizan campos proporcionados (exclude_unset)
        - id y created_at se preservan sin cambios
        """
        guest = self.repository.get_by_id(guest_id)
        if guest is None:
            raise GuestNotFoundException()

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data:
            new_email = update_data["email"]
            if new_email != guest.email:
                existing = self.repository.get_by_email(new_email)
                if existing is not None:
                    raise GuestEmailDuplicateException()

        # Determine the identification pair after the potential update to
        # detect whether the resulting (type, number) collides with another guest.
        new_type = update_data.get(
            "identification_type", guest.identification_type
        )
        new_number = update_data.get(
            "identification_number", guest.identification_number
        )
        identification_changed = (
            new_type != guest.identification_type
            or new_number != guest.identification_number
        )
        if identification_changed:
            existing = self.repository.get_by_identification(
                new_type, new_number
            )
            if existing is not None and existing.id != guest.id:
                raise GuestIdentificationDuplicateException()

        for field, value in update_data.items():
            setattr(guest, field, value)

        updated_guest = self.repository.update(guest)

        try:
            audit_log("update", updated_guest.id, "success")
        except Exception:
            audit_log("update", updated_guest.id, "failure")

        return updated_guest
