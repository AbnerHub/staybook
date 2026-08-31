from datetime import date

from sqlalchemy.orm import Session

from app.models.reservation import Reservation, ReservationStatus

# Estados de reserva que se consideran "activos" para bloquear disponibilidad /
# solapamiento. Fuente única compartida por get_active_overlapping y las
# consultas de disponibilidad, para evitar divergencia de reglas.
_ACTIVE_STATUSES = (
    ReservationStatus.CONFIRMED,
    ReservationStatus.CHECKED_IN,
)


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

        Participan las reservas activas, es decir con status 'confirmed' o
        'checked_in'. Las reservas 'cancelled' y 'checked_out' se excluyen. Si
        se provee exclude_id, esa reserva se excluye del resultado
        (auto-exclusión durante la actualización).
        """
        query = (
            self.db.query(Reservation)
            .filter(Reservation.room_id == room_id)
            .filter(Reservation.status.in_(_ACTIVE_STATUSES))
            .filter(Reservation.check_in_date < check_out)
            .filter(Reservation.check_out_date > check_in)
        )
        if exclude_id is not None:
            query = query.filter(Reservation.id != exclude_id)
        return query.all()

    def get_room_ids_with_active_overlap(
        self, check_in: date, check_out: date
    ) -> set[int]:
        """
        Retornar el conjunto de room_id que tienen al menos una reserva activa
        (confirmed o checked_in) cuyo rango [check_in_date, check_out_date) se
        solapa con [check_in, check_out).

        Consulta única (DISTINCT room_id) para evitar N+1 al calcular
        disponibilidad por rango.
        """
        rows = (
            self.db.query(Reservation.room_id)
            .filter(Reservation.status.in_(_ACTIVE_STATUSES))
            .filter(Reservation.check_in_date < check_out)
            .filter(Reservation.check_out_date > check_in)
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    def query_history(
        self,
        guest_id: int | None = None,
        room_id: int | None = None,
        status: ReservationStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Reservation]:
        """
        Consultar el historial de reservas aplicando solo los filtros provistos
        (combinación AND). Consulta única, de solo lectura.

        El filtro por rango de fechas usa la intersección semiabierta
        (check_in_date < date_to AND check_out_date > date_from) y solo se
        aplica cuando date_from y date_to están ambos presentes (la validación
        both-or-neither se realiza en la capa de query params).
        """
        query = self.db.query(Reservation)
        if guest_id is not None:
            query = query.filter(Reservation.guest_id == guest_id)
        if room_id is not None:
            query = query.filter(Reservation.room_id == room_id)
        if status is not None:
            query = query.filter(Reservation.status == status)
        if date_from is not None and date_to is not None:
            query = query.filter(Reservation.check_in_date < date_to)
            query = query.filter(Reservation.check_out_date > date_from)
        return query.all()
