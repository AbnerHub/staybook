"""Query service — read-only history / occupancy / availability logic."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.room_repository import RoomRepository


@dataclass
class OccupancySummary:
    """Resumen interno de ocupación (mapeado a OccupancySummaryResponse)."""

    total_rooms: int
    occupied_rooms: int
    available_rooms: int
    maintenance_rooms: int
    occupancy_rate: float


@dataclass
class HistoryFilters:
    """Filtros normalizados para el historial de reservas."""

    guest_id: int | None = None
    room_id: int | None = None
    status: ReservationStatus | None = None
    date_from: date | None = None
    date_to: date | None = None


class QueryService:
    """Servicio de consultas de solo lectura.

    Deriva todas sus respuestas de las tablas existentes (rooms, reservations)
    reutilizando los repositorios. No realiza escrituras ni mantiene una
    segunda fuente de verdad.
    """

    def __init__(
        self,
        room_repository: RoomRepository,
        reservation_repository: ReservationRepository,
        today_provider: Callable[[], date] = date.today,
    ):
        self.room_repository = room_repository
        self.reservation_repository = reservation_repository
        self._today = today_provider

    def get_current_occupancy(self) -> OccupancySummary:
        """
        Derivar la ocupación actual del estado operativo de las habitaciones.

        occupancy_rate = occupied / total, con guarda de división por cero.
        """
        total = self.room_repository.count_all()
        occupied = self.room_repository.count_by_status(RoomStatus.OCUPADA)
        available = self.room_repository.count_by_status(RoomStatus.DISPONIBLE)
        maintenance = self.room_repository.count_by_status(
            RoomStatus.MANTENIMIENTO
        )
        occupancy_rate = (occupied / total) if total > 0 else 0.0
        return OccupancySummary(
            total_rooms=total,
            occupied_rooms=occupied,
            available_rooms=available,
            maintenance_rooms=maintenance,
            occupancy_rate=occupancy_rate,
        )

    def list_occupied_rooms(self) -> list[Room]:
        """Retornar las habitaciones cuyo estado operativo es 'ocupada'."""
        return self.room_repository.get_by_status(RoomStatus.OCUPADA)

    def list_available_rooms(
        self, check_in: date, check_out: date
    ) -> list[Room]:
        """
        Retornar las habitaciones disponibles para el rango [check_in, check_out).

        Una habitación está disponible sii:
        - su estado NO es 'mantenimiento', Y
        - no tiene ninguna reserva activa (confirmed/checked_in) solapada.

        No se exige que el estado sea 'disponible': una habitación ocupada hoy
        puede estar libre para un rango futuro.

        Implementación con número constante de consultas (sin N+1):
        1) ids de habitaciones con solapamiento activo (1 consulta)
        2) habitaciones que no están en mantenimiento (1 consulta)
        3) diferencia en memoria
        """
        blocked_room_ids = (
            self.reservation_repository.get_room_ids_with_active_overlap(
                check_in, check_out
            )
        )
        candidate_rooms = self.room_repository.get_not_in_maintenance()
        return [r for r in candidate_rooms if r.id not in blocked_room_ids]

    def get_reservation_history(
        self, filters: HistoryFilters
    ) -> list[Reservation]:
        """Retornar el historial de reservas aplicando los filtros provistos."""
        return self.reservation_repository.query_history(
            guest_id=filters.guest_id,
            room_id=filters.room_id,
            status=filters.status,
            date_from=filters.date_from,
            date_to=filters.date_to,
        )
