from datetime import date

from sqlalchemy.orm import Session

from app.models.reservation import Reservation, ReservationStatus


class ReservationRepository:
    """Capa de acceso a datos para la entidad Reservation."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, reservation: Reservation) -> Reservation:
        """Insertar una nueva reserva."""
        self.db.add(reservation)
        self.db.flush()
        self.db.refresh(reservation)
        return reservation

    def get_by_id(self, reservation_id: int) -> Reservation | None:
        """Buscar reserva por ID. Retorna None si no existe."""
        return self.db.get(Reservation, reservation_id)

    def get_all(self) -> list[Reservation]:
        """Retornar todas las reservas (confirmed y cancelled)."""
        return self.db.query(Reservation).all()

    def update(self, reservation: Reservation) -> Reservation:
        """Persistir cambios en una reserva existente."""
        self.db.flush()
        self.db.refresh(reservation)
        return reservation

    def get_active_overlapping(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
        exclude_id: int | None = None,
    ) -> list[Reservation]:
        """
        Retornar reservas 'confirmed' de la habitación cuyo rango
        [check_in_date, check_out_date) se solapa con [check_in, check_out).

        Regla de solapamiento (intervalo semiabierto):
            existing.check_in_date < check_out AND existing.check_out_date > check_in

        Solo participan reservas con status 'confirmed'. Si se provee
        exclude_id, esa reserva se excluye del resultado (auto-exclusión
        durante la actualización).
        """
        query = (
            self.db.query(Reservation)
            .filter(Reservation.room_id == room_id)
            .filter(Reservation.status == ReservationStatus.CONFIRMED)
            .filter(Reservation.check_in_date < check_out)
            .filter(Reservation.check_out_date > check_in)
        )
        if exclude_id is not None:
            query = query.filter(Reservation.id != exclude_id)
        return query.all()
