"""Stay service — operational lifecycle (check-in / check-out) for reservations."""

from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import (
    CheckInDateNotAllowedException,
    ReservationInvalidTransitionException,
    ReservationNotFoundException,
    RoomNotFoundException,
)
from app.core.logging import audit_log
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository


class StayService:
    """Gestiona el ciclo de vida operativo (check-in / check-out) de una reserva.

    Coordina, de forma atómica, el cambio de estado de la reserva y el cambio
    del estado operativo de la habitación asociada. El servicio posee el
    commit/rollback de su operación sobre la MISMA Session que comparten sus
    repositorios; los repositorios solo hacen flush/refresh. Nunca modifica el
    estado de la habitación fuera de las dos transiciones definidas.
    """

    def __init__(
        self,
        session: Session,
        reservation_repository: ReservationRepository,
        room_repository: RoomRepository,
        today_provider: Callable[[], date] = date.today,
    ):
        self.session = session
        self.reservation_repository = reservation_repository
        self.room_repository = room_repository
        self._today = today_provider

    def check_in(self, reservation_id: int) -> Reservation:
        """
        Registrar el check-in de una reserva confirmada.

        Reglas:
        - La reserva debe existir (ReservationNotFoundException, 404)
        - status debe ser 'confirmed' (ReservationInvalidTransitionException, 409)
        - check_in_date <= today < check_out_date
          (CheckInDateNotAllowedException, 409)
        - reservation.status -> checked_in ; room.status -> OCUPADA (misma transacción)
        """
        reservation = self.reservation_repository.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundException()

        if reservation.status != ReservationStatus.CONFIRMED:
            raise ReservationInvalidTransitionException()

        today = self._today()
        if today < reservation.check_in_date:
            raise CheckInDateNotAllowedException(
                detail="El check-in no está permitido antes de la fecha de entrada"
            )
        if today >= reservation.check_out_date:
            raise CheckInDateNotAllowedException(
                detail=(
                    "El check-in no está permitido en o después de la fecha de salida"
                )
            )

        room = self.room_repository.get_by_id(reservation.room_id)
        if room is None:
            raise RoomNotFoundException()

        reservation.status = ReservationStatus.CHECKED_IN
        room.status = RoomStatus.OCUPADA

        return self._commit_atomic(reservation, room, "check_in")

    def check_out(self, reservation_id: int) -> Reservation:
        """
        Registrar el check-out de una reserva con check-in realizado.

        Reglas:
        - La reserva debe existir (ReservationNotFoundException, 404)
        - status debe ser 'checked_in' (ReservationInvalidTransitionException, 409)
        - reservation.status -> checked_out ; room.status -> DISPONIBLE (misma
          transacción). Permitido en cualquier fecha mientras esté checked_in.
        """
        reservation = self.reservation_repository.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundException()

        if reservation.status != ReservationStatus.CHECKED_IN:
            raise ReservationInvalidTransitionException()

        room = self.room_repository.get_by_id(reservation.room_id)
        if room is None:
            raise RoomNotFoundException()

        reservation.status = ReservationStatus.CHECKED_OUT
        room.status = RoomStatus.DISPONIBLE

        return self._commit_atomic(reservation, room, "check_out")

    def _commit_atomic(
        self, reservation: Reservation, room: Room, operation: str
    ) -> Reservation:
        """Persistir reserva + habitación en una única transacción atómica.

        Ambos update hacen flush sobre la misma Session; un único commit
        confirma los dos cambios juntos. Ante cualquier fallo, se hace rollback
        de ambos cambios y se relanza la excepción.
        """
        try:
            self.reservation_repository.update(reservation)
            self.room_repository.update(room)
            self.session.commit()
        except Exception:
            self.session.rollback()
            self._safe_audit(operation, reservation.id, "failure")
            raise

        self._safe_audit(operation, reservation.id, "success")
        return reservation

    @staticmethod
    def _safe_audit(operation: str, reservation_id: int, result: str) -> None:
        """Emit an audit event without letting a logging failure break the flow."""
        try:
            audit_log(operation, reservation_id, result)
        except Exception:
            # Audit logging must never interrupt the operational flow.
            audit_log(operation, reservation_id, "failure")
