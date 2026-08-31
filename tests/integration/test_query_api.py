"""Integration tests for history / occupancy / availability query endpoints."""

import time
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings as app_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.guest import Guest, IdentificationType
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine)


@pytest.fixture()
def client(engine, session_factory):
    def _override_get_db():
        db = session_factory()
        try:
            yield db
            db.commit()
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def admin_headers():
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) + 3600}
    token = jwt.encode(
        payload, app_settings.secret_key, algorithm=app_settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


def _seed(session_factory, rooms=None, reservations=None):
    s = session_factory()
    s.add(
        Guest(
            first_name="John", last_name="Doe", email="john@example.com",
            phone="5551234", identification_type=IdentificationType.NATIONAL_ID,
            identification_number="X1",
        )
    )
    for number, status in (rooms or []):
        s.add(
            Room(
                room_number=number, room_type=RoomType.INDIVIDUAL,
                price_per_night=Decimal("100.00"), capacity=2, status=status,
            )
        )
    s.flush()
    for room_id, ci, co, status in (reservations or []):
        s.add(
            Reservation(
                guest_id=1, room_id=room_id, check_in_date=ci, check_out_date=co,
                status=status, total_price=Decimal("400.00"),
            )
        )
    s.commit()
    s.close()


class TestOccupancy:
    def test_summary(self, client, session_factory, admin_headers):
        _seed(session_factory, rooms=[
            ("101", RoomStatus.OCUPADA),
            ("102", RoomStatus.DISPONIBLE),
            ("103", RoomStatus.MANTENIMIENTO),
            ("104", RoomStatus.OCUPADA),
        ])
        resp = client.get("/api/v1/occupancy/current", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rooms"] == 4
        assert data["occupied_rooms"] == 2
        assert data["available_rooms"] == 1
        assert data["maintenance_rooms"] == 1
        assert data["occupancy_rate"] == pytest.approx(0.5)

    def test_summary_empty_no_division_by_zero(self, client, admin_headers):
        resp = client.get("/api/v1/occupancy/current", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rooms"] == 0
        assert data["occupancy_rate"] == 0.0

    def test_occupied_rooms(self, client, session_factory, admin_headers):
        _seed(session_factory, rooms=[
            ("101", RoomStatus.OCUPADA),
            ("102", RoomStatus.DISPONIBLE),
        ])
        resp = client.get("/api/v1/occupancy/rooms", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["room_number"] == "101"
        assert body[0]["status"] == "ocupada"

    def test_occupied_rooms_empty(self, client, session_factory, admin_headers):
        _seed(session_factory, rooms=[("102", RoomStatus.DISPONIBLE)])
        resp = client.get("/api/v1/occupancy/rooms", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestAvailability:
    def test_occupied_now_available_future(self, client, session_factory, admin_headers):
        # Room 101 is OCUPADA now with a checked_in reservation ending Sep 5.
        _seed(
            session_factory,
            rooms=[("101", RoomStatus.OCUPADA)],
            reservations=[
                (1, date(2026, 9, 1), date(2026, 9, 5), ReservationStatus.CHECKED_IN)
            ],
        )
        resp = client.get(
            "/api/v1/availability",
            params={"check_in_date": "2026-09-10", "check_out_date": "2026-09-12"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert [r["room_number"] for r in resp.json()] == ["101"]

    def test_maintenance_never_available(self, client, session_factory, admin_headers):
        _seed(session_factory, rooms=[("101", RoomStatus.MANTENIMIENTO)])
        resp = client.get(
            "/api/v1/availability",
            params={"check_in_date": "2026-09-01", "check_out_date": "2026-09-05"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_adjacent_not_blocked(self, client, session_factory, admin_headers):
        _seed(
            session_factory,
            rooms=[("101", RoomStatus.DISPONIBLE)],
            reservations=[
                (1, date(2026, 9, 1), date(2026, 9, 5), ReservationStatus.CONFIRMED)
            ],
        )
        resp = client.get(
            "/api/v1/availability",
            params={"check_in_date": "2026-09-05", "check_out_date": "2026-09-08"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert [r["room_number"] for r in resp.json()] == ["101"]

    def test_active_overlap_blocks(self, client, session_factory, admin_headers):
        _seed(
            session_factory,
            rooms=[("101", RoomStatus.DISPONIBLE)],
            reservations=[
                (1, date(2026, 9, 1), date(2026, 9, 5), ReservationStatus.CONFIRMED)
            ],
        )
        resp = client.get(
            "/api/v1/availability",
            params={"check_in_date": "2026-09-03", "check_out_date": "2026-09-07"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_cancelled_and_checked_out_do_not_block(
        self, client, session_factory, admin_headers
    ):
        _seed(
            session_factory,
            rooms=[("101", RoomStatus.DISPONIBLE)],
            reservations=[
                (1, date(2026, 9, 1), date(2026, 9, 5), ReservationStatus.CANCELLED),
                (1, date(2026, 9, 1), date(2026, 9, 5), ReservationStatus.CHECKED_OUT),
            ],
        )
        resp = client.get(
            "/api/v1/availability",
            params={"check_in_date": "2026-09-02", "check_out_date": "2026-09-04"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert [r["room_number"] for r in resp.json()] == ["101"]

    def test_invalid_range_422(self, client, admin_headers):
        resp = client.get(
            "/api/v1/availability",
            params={"check_in_date": "2026-09-05", "check_out_date": "2026-09-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_missing_param_422(self, client, admin_headers):
        resp = client.get(
            "/api/v1/availability",
            params={"check_in_date": "2026-09-05"},
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestHistory:
    def _seed_history(self, session_factory):
        _seed(
            session_factory,
            rooms=[("101", RoomStatus.DISPONIBLE), ("102", RoomStatus.DISPONIBLE)],
            reservations=[
                (1, date(2026, 9, 1), date(2026, 9, 5), ReservationStatus.CONFIRMED),
                (1, date(2026, 10, 1), date(2026, 10, 5), ReservationStatus.CHECKED_OUT),
                (2, date(2026, 9, 1), date(2026, 9, 3), ReservationStatus.CANCELLED),
            ],
        )

    def test_no_filters_all_statuses(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get("/api/v1/history/reservations", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_combined_filters(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get(
            "/api/v1/history/reservations",
            params={"room_id": 1, "status": "confirmed"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["room_id"] == 1

    def test_nonexistent_id_empty(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get(
            "/api/v1/history/reservations",
            params={"guest_id": 9999},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_date_range_both_provided(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get(
            "/api/v1/history/reservations",
            params={"date_from": "2026-09-01", "date_to": "2026-09-30"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2  # the two September reservations

    def test_only_date_from_422(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get(
            "/api/v1/history/reservations",
            params={"date_from": "2026-09-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_only_date_to_422(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get(
            "/api/v1/history/reservations",
            params={"date_to": "2026-09-30"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_both_omitted_ok(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get("/api/v1/history/reservations", headers=admin_headers)
        assert resp.status_code == 200

    def test_bad_date_order_422(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get(
            "/api/v1/history/reservations",
            params={"date_from": "2026-09-30", "date_to": "2026-09-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_status_outside_enum_422(self, client, session_factory, admin_headers):
        self._seed_history(session_factory)
        resp = client.get(
            "/api/v1/history/reservations",
            params={"status": "not_a_status"},
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestConstantQueryAvailability:
    def test_no_n_plus_one(self, session_factory):
        """list_available_rooms issues a constant number of SQL statements
        regardless of the number of rooms."""
        from app.repositories.reservation_repository import ReservationRepository
        from app.repositories.room_repository import RoomRepository
        from app.services.query_service import QueryService

        def _count_statements(n_rooms: int) -> int:
            # Fresh DB per measurement
            eng = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            Base.metadata.create_all(eng)
            sf = sessionmaker(bind=eng)
            s = sf()
            for i in range(n_rooms):
                s.add(
                    Room(
                        room_number=f"R{i}", room_type=RoomType.INDIVIDUAL,
                        price_per_night=Decimal("100.00"), capacity=2,
                        status=RoomStatus.DISPONIBLE,
                    )
                )
            s.commit()

            service = QueryService(
                room_repository=RoomRepository(s),
                reservation_repository=ReservationRepository(s),
            )

            counter = {"n": 0}

            def _before_cursor(conn, cursor, statement, *args):
                counter["n"] += 1

            event.listen(eng, "before_cursor_execute", _before_cursor)
            service.list_available_rooms(date(2026, 9, 1), date(2026, 9, 5))
            event.remove(eng, "before_cursor_execute", _before_cursor)
            s.close()
            eng.dispose()
            return counter["n"]

        small = _count_statements(2)
        large = _count_statements(50)
        # Same constant number of statements regardless of room count.
        assert small == large


class TestReadOnly:
    def test_queries_do_not_mutate_state(self, client, session_factory, admin_headers):
        _seed(
            session_factory,
            rooms=[("101", RoomStatus.OCUPADA), ("102", RoomStatus.DISPONIBLE)],
            reservations=[
                (2, date(2026, 9, 1), date(2026, 9, 5), ReservationStatus.CONFIRMED)
            ],
        )

        def _snapshot():
            s = session_factory()
            try:
                rooms = {r.id: r.status for r in s.query(Room).all()}
                res = {r.id: r.status for r in s.query(Reservation).all()}
                return rooms, res
            finally:
                s.close()

        before = _snapshot()
        client.get("/api/v1/occupancy/current", headers=admin_headers)
        client.get("/api/v1/occupancy/rooms", headers=admin_headers)
        client.get(
            "/api/v1/availability",
            params={"check_in_date": "2026-09-10", "check_out_date": "2026-09-12"},
            headers=admin_headers,
        )
        client.get("/api/v1/history/reservations", headers=admin_headers)
        after = _snapshot()
        assert before == after
