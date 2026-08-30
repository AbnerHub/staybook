"""Reservation service — business logic layer for reservation management."""

from decimal import Decimal

from app.core.exceptions import (
    GuestNotFoundException,
    ReservationAlreadyCancelledException,
    ReservationCancelledNotEditableException,
    ReservationInvalidDatesException,
    ReservationNotFoundException,
    ReservationOverlapException,
    RoomNotFoundException,
)
from app.core.logging import audit_log
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room
from app.repositories.guest_repository import GuestRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.reservation import ReservationCreate, ReservationUpdate


class ReservationService:
    """Servicio de reservas. Aplica reglas de negocio y coordina operaciones.

    Reutiliza los repositorios existentes de Room y Guest para validar la
    existencia de las entidades y obtener el precio por noche de la habitación.
    Nunca modifica el estado (status) de la Habitación.
    """

    def __init__(
        self,
        repository: ReservationRepository,
        room_repository: RoomRepository,
        guest_repository: GuestRepository,
    ):
        self.repository = repository
        self.room_repository = room_repository
        self.guest_repository = guest_repository

    def _calculate_total_price(
        self, room: Room, check_in, check_out
    ) -> Decimal:
        """Precio total = número de noches * precio por noche de la habitación."""
        nights = (check_out - check_in).days
        return Decimal(nights) * room.price_per_night

    def create_reservation(self, data: ReservationCreate) -> Reservation:
        """
        Crear reserva.

        Reglas:
        - El huésped debe existir (GuestNotFoundException)
        - La habitación debe existir (RoomNotFoundException)
        - check_out_date > check_in_date (ReservationInvalidDatesException)
        - Sin solapamiento con reservas activas (ReservationOverlapException)
        - total_price calculado por el servidor
        """
        if self.guest_repository.get_by_id(data.guest_id) is None:
            raise GuestNotFoundException()

        room = self.room_repository.get_by_id(data.room_id)
        if room is None:
            raise RoomNotFoundException()

        if data.check_out_date <= data.check_in_date:
            raise ReservationInvalidDatesException()

        overlapping = self.repository.get_active_overlapping(
            room_id=data.room_id,
            check_in=data.check_in_date,
            check_out=data.check_out_date,
        )
        if overlapping:
            raise ReservationOverlapException()

        total_price = self._calculate_total_price(
            room, data.check_in_date, data.check_out_date
        )

        reservation = Reservation(
            guest_id=data.guest_id,
            room_id=data.room_id,
            check_in_date=data.check_in_date,
            check_out_date=data.check_out_date,
            status=ReservationStatus.CONFIRMED,
            total_price=total_price,
        )

        created = self.repository.create(reservation)

        try:
            audit_log("create", created.id, "success")
        except Exception:
            audit_log("create", created.id, "failure")

        return created

    def list_reservations(self) -> list[Reservation]:
        """Retornar todas las reservas (confirmed y cancelled)."""
        return self.repository.get_all()

    def get_reservation(self, reservation_id: int) -> Reservation:
        """
        Obtener reserva por ID.

        Lanza ReservationNotFoundException si no existe.
        """
        reservation = self.repository.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundException()
        return reservation

    def update_reservation(
        self, reservation_id: int, data: ReservationUpdate
    ) -> Reservation:
        """
        Actualización parcial sobre el estado resultante.

        Reglas:
        - La reserva debe existir (ReservationNotFoundException)
        - Una reserva cancelada no puede modificarse
          (ReservationCancelledNotEditableException)
        - El estado resultante se construye combinando los valores actuales
          con los cambios provistos (solo room_id, check_in_date, check_out_date)
        - Se valida la existencia de la habitación resultante, las fechas
          resultantes y el solapamiento (excluyendo la propia reserva)
        - Se recalcula total_price sobre el estado resultante
        """
        reservation = self.repository.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundException()

        if reservation.status == ReservationStatus.CANCELLED:
            raise ReservationCancelledNotEditableException()

        update_data = data.model_dump(exclude_unset=True)

        # Estado resultante: valores actuales combinados con los cambios provistos.
        result_room_id = update_data.get("room_id", reservation.room_id)
        result_check_in = update_data.get(
            "check_in_date", reservation.check_in_date
        )
        result_check_out = update_data.get(
            "check_out_date", reservation.check_out_date
        )

        room = self.room_repository.get_by_id(result_room_id)
        if room is None:
            raise RoomNotFoundException()

        if result_check_out <= result_check_in:
            raise ReservationInvalidDatesException()

        overlapping = self.repository.get_active_overlapping(
            room_id=result_room_id,
            check_in=result_check_in,
            check_out=result_check_out,
            exclude_id=reservation.id,
        )
        if overlapping:
            raise ReservationOverlapException()

        reservation.room_id = result_room_id
        reservation.check_in_date = result_check_in
        reservation.check_out_date = result_check_out
        reservation.total_price = self._calculate_total_price(
            room, result_check_in, result_check_out
        )

        updated = self.repository.update(reservation)

        try:
            audit_log("update", updated.id, "success")
        except Exception:
            audit_log("update", updated.id, "failure")

        return updated

    def cancel_reservation(self, reservation_id: int) -> Reservation:
        """
        Cancelar reserva (cambio de estado, sin borrado físico).

        Reglas:
        - La reserva debe existir (ReservationNotFoundException)
        - No puede estar ya cancelada (ReservationAlreadyCancelledException)
        - Solo cambia status a 'cancelled'; los demás campos se preservan
        """
        reservation = self.repository.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundException()

        if reservation.status == ReservationStatus.CANCELLED:
            raise ReservationAlreadyCancelledException()

        reservation.status = ReservationStatus.CANCELLED

        updated = self.repository.update(reservation)

        try:
            audit_log("cancel", updated.id, "success")
        except Exception:
            audit_log("cancel", updated.id, "failure")

        return updated
