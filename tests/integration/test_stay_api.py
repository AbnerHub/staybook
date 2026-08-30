"""Integration tests for the Check-in / Check-out API endpoints.

Validates Requirements: 2.x, 3.2, 3.3, 4.x, 5.1, 6.x, 7.3, 7.4, 9.3, 9.4, 9.5
"""

import time
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings as app_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.guest import Guest, IdentificationType
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType

# Dates spanning the real current date so the default today_provider (date.today)
# allows check-in: check_in_date <= today < check_out_date.
TODAY = date.today()  # noqa: DTZ011 — MVP uses hotel-local date, matching the service default
CURRENT_CHECK_IN = TODAY - timedelta(days=1)
CURRENT_CHECK_OUT = TODAY + timedelta(days=3)
# A future window (today < check_in_date) to test early check-in rejection.
FUTURE_CHECK_IN = TODAY + timedelta(days=10)
FUTURE_CHECK_OUT = TODAY + timedelta(days=15)
# A past window (today >= check_out_date) to test late check-in rejection.
PAST_CHECK_IN = TODAY - timedelta(days=10)
PAST_CHECK_OUT = TODAY - timedelta(days=5)


@pytest.fixture()
def make_client():
    """Return a factory that builds a TestClient seeded with a room, a guest,
    and one reservation with the given dates/status."""
    engines = []

    def _build(
        check_in: date = CURRENT_CHECK_IN,
        check_out: date = CURRENT_CHECK_OUT,
        status: ReservationStatus = ReservationStatus.CONFIRMED,
    ) -> TestClient:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        engines.append(engine)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)

        seed = session_factory()
        seed.add(
            Guest(
                first_name="John", last_name="Doe", email="john@example.com",
                phone="5551234",
                identification_type=IdentificationType.NATIONAL_ID,
                identification_number="X1",
            )
        )
        seed.add(
            Room(
                room_number="101", room_type=RoomType.INDIVIDUAL,
                price_per_night=Decimal("100.00"), capacity=2,
                status=RoomStatus.DISPONIBLE,
            )
        )
        seed.flush()
        seed.add(
            Reservation(
                guest_id=1, room_id=1,
                check_in_date=check_in, check_out_date=check_out,
                status=status, total_price=Decimal("400.00"),
            )
        )
        seed.commit()
        seed.close()

        def _override_get_db():
            db = session_factory()
            try:
                yield db
                db.commit()
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override_get_db
        return TestClient(app)

    yield _build

    app.dependency_overrides.pop(get_db, None)
    for e in engines:
        e.dispose()


@pytest.fixture()
def admin_headers():
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) + 3600}
    token = jwt.encode(
        payload, app_settings.secret_key, algorithm=app_settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


class TestCheckIn:
    def test_check_in_success_sets_checked_in_and_room_occupied(
        self, make_client, admin_headers
    ):
        client = make_client()
        resp = client.post("/api/v1/reservations/1/check-in", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "checked_in"
        room = client.get("/api/v1/rooms/1", headers=admin_headers).json()
        assert room["status"] == "ocupada"

    def test_check_in_missing_reservation_404(self, make_client, admin_headers):
        client = make_client()
        resp = client.post("/api/v1/reservations/999/check-in", headers=admin_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "La reserva no fue encontrada"

    def test_check_in_wrong_status_409(self, make_client, admin_headers):
        client = make_client(status=ReservationStatus.CANCELLED)
        resp = client.post("/api/v1/reservations/1/check-in", headers=admin_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"] == "La transición de estado de la reserva no es válida"

    def test_double_check_in_409(self, make_client, admin_headers):
        client = make_client()
        first = client.post("/api/v1/reservations/1/check-in", headers=admin_headers)
        assert first.status_code == 200
        second = client.post("/api/v1/reservations/1/check-in", headers=admin_headers)
        assert second.status_code == 409

    def test_early_check_in_409(self, make_client, admin_headers):
        client = make_client(check_in=FUTURE_CHECK_IN, check_out=FUTURE_CHECK_OUT)
        resp = client.post("/api/v1/reservations/1/check-in", headers=admin_headers)
        assert resp.status_code == 409

    def test_late_check_in_409(self, make_client, admin_headers):
        client = make_client(check_in=PAST_CHECK_IN, check_out=PAST_CHECK_OUT)
        resp = client.post("/api/v1/reservations/1/check-in", headers=admin_headers)
        assert resp.status_code == 409

    def test_invalid_id_format_422(self, make_client, admin_headers):
        client = make_client()
        resp = client.post("/api/v1/reservations/abc/check-in", headers=admin_headers)
        assert resp.status_code == 422


class TestCheckOut:
    def test_check_out_success_sets_checked_out_and_room_available(
        self, make_client, admin_headers
    ):
        client = make_client(status=ReservationStatus.CHECKED_IN)
        resp = client.post("/api/v1/reservations/1/check-out", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "checked_out"
        room = client.get("/api/v1/rooms/1", headers=admin_headers).json()
        assert room["status"] == "disponible"

    def test_check_out_missing_reservation_404(self, make_client, admin_headers):
        client = make_client(status=ReservationStatus.CHECKED_IN)
        resp = client.post("/api/v1/reservations/999/check-out", headers=admin_headers)
        assert resp.status_code == 404

    def test_check_out_wrong_status_409(self, make_client, admin_headers):
        client = make_client(status=ReservationStatus.CONFIRMED)
        resp = client.post("/api/v1/reservations/1/check-out", headers=admin_headers)
        assert resp.status_code == 409

    def test_double_check_out_409(self, make_client, admin_headers):
        client = make_client(status=ReservationStatus.CHECKED_IN)
        first = client.post("/api/v1/reservations/1/check-out", headers=admin_headers)
        assert first.status_code == 200
        second = client.post("/api/v1/reservations/1/check-out", headers=admin_headers)
        assert second.status_code == 409


class TestPatchCannotEditStatus:
    def test_patch_status_returns_422(self, make_client, admin_headers):
        """Req 7.3: PATCH must reject a client-sent status (extra=forbid)."""
        client = make_client()
        resp = client.patch(
            "/api/v1/reservations/1", json={"status": "checked_in"},
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestOverlapWithCheckedIn:
    def test_checked_in_blocks_and_checkout_frees(self, make_client, admin_headers):
        # Reservation 1 is checked_in over [today-1, today+3)
        client = make_client(status=ReservationStatus.CHECKED_IN)

        overlapping = {
            "guest_id": 1,
            "room_id": 1,
            "check_in_date": TODAY.isoformat(),
            "check_out_date": (TODAY + timedelta(days=2)).isoformat(),
        }
        # While checked_in → overlap blocked (409)
        blocked = client.post(
            "/api/v1/reservations/", json=overlapping, headers=admin_headers
        )
        assert blocked.status_code == 409

        # After check-out → range is free again (201)
        client.post("/api/v1/reservations/1/check-out", headers=admin_headers)
        freed = client.post(
            "/api/v1/reservations/", json=overlapping, headers=admin_headers
        )
        assert freed.status_code == 201
