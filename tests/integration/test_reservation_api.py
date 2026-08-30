"""Integration tests for the Reservation Management API endpoints.

Validates Requirements: 1.5, 2.1, 2.2, 3.1, 4.2, 4.3, 5.2, 6.2, 7.3, 7.4,
7.9, 7.10, 8.1, 8.4, 8.5, 10.2, 10.4, 10.5
"""

import time
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
from app.models.room import Room, RoomStatus, RoomType


@pytest.fixture()
def client():
    """TestClient with a shared in-memory SQLite DB, seeded with a guest and room."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    # Seed one guest (id=1) and one room (id=1, price 100.00) for FK references.
    seed = session_factory()
    seed.add(
        Guest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="5551234",
            identification_type=IdentificationType.NATIONAL_ID,
            identification_number="X1",
        )
    )
    seed.add(
        Room(
            room_number="101",
            room_type=RoomType.INDIVIDUAL,
            price_per_night=Decimal("100.00"),
            capacity=2,
            status=RoomStatus.DISPONIBLE,
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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


@pytest.fixture()
def admin_headers():
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) + 3600}
    token = jwt.encode(
        payload, app_settings.secret_key, algorithm=app_settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


def _body(**overrides) -> dict:
    body = {
        "guest_id": 1,
        "room_id": 1,
        "check_in_date": "2026-09-01",
        "check_out_date": "2026-09-05",
    }
    body.update(overrides)
    return body


class TestCreate:
    def test_create_returns_201_and_total_price(self, client, admin_headers):
        resp = client.post("/api/v1/reservations/", json=_body(), headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] is not None
        assert data["status"] == "confirmed"
        # 4 nights * 100.00
        assert Decimal(str(data["total_price"])) == Decimal("400.00")

    def test_invalid_dates_returns_422(self, client, admin_headers):
        resp = client.post(
            "/api/v1/reservations/",
            json=_body(check_out_date="2026-08-31"),
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_client_total_price_returns_422(self, client, admin_headers):
        resp = client.post(
            "/api/v1/reservations/",
            json=_body(total_price="1.00"),
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_client_status_returns_422(self, client, admin_headers):
        resp = client.post(
            "/api/v1/reservations/",
            json=_body(status="cancelled"),
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_missing_guest_returns_404(self, client, admin_headers):
        resp = client.post(
            "/api/v1/reservations/",
            json=_body(guest_id=999),
            headers=admin_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "El huésped no fue encontrado"

    def test_missing_room_returns_404(self, client, admin_headers):
        resp = client.post(
            "/api/v1/reservations/",
            json=_body(room_id=999),
            headers=admin_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "La habitación no fue encontrada"

    def test_overlap_returns_409(self, client, admin_headers):
        client.post("/api/v1/reservations/", json=_body(), headers=admin_headers)
        resp = client.post(
            "/api/v1/reservations/",
            json=_body(check_in_date="2026-09-03", check_out_date="2026-09-07"),
            headers=admin_headers,
        )
        assert resp.status_code == 409

    def test_adjacent_reservations_allowed(self, client, admin_headers):
        r1 = client.post(
            "/api/v1/reservations/",
            json=_body(check_in_date="2026-09-01", check_out_date="2026-09-05"),
            headers=admin_headers,
        )
        assert r1.status_code == 201
        r2 = client.post(
            "/api/v1/reservations/",
            json=_body(check_in_date="2026-09-05", check_out_date="2026-09-08"),
            headers=admin_headers,
        )
        assert r2.status_code == 201


class TestListAndGet:
    def test_empty_list(self, client, admin_headers):
        resp = client.get("/api/v1/reservations/", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_by_id(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        resp = client.get(
            f"/api/v1/reservations/{created['id']}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_not_found_returns_404(self, client, admin_headers):
        resp = client.get("/api/v1/reservations/999", headers=admin_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "La reserva no fue encontrada"


class TestUpdate:
    def test_partial_update_recalculates_price(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        resp = client.patch(
            f"/api/v1/reservations/{created['id']}",
            json={"check_out_date": "2026-09-08"},  # 7 nights
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["check_in_date"] == "2026-09-01"  # preserved
        assert Decimal(str(data["total_price"])) == Decimal("700.00")

    def test_update_not_found_returns_404(self, client, admin_headers):
        resp = client.patch(
            "/api/v1/reservations/999",
            json={"check_out_date": "2026-09-08"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_update_client_total_price_returns_422(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        resp = client.patch(
            f"/api/v1/reservations/{created['id']}",
            json={"total_price": "1.00"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_update_same_range_self_exclusion(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        # Re-submit the same check_in: overlap check must exclude the reservation itself.
        resp = client.patch(
            f"/api/v1/reservations/{created['id']}",
            json={"check_in_date": "2026-09-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 200


class TestCancel:
    def test_cancel_returns_200_and_status_cancelled(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        resp = client.post(
            f"/api/v1/reservations/{created['id']}/cancel", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_not_found_returns_404(self, client, admin_headers):
        resp = client.post(
            "/api/v1/reservations/999/cancel", headers=admin_headers
        )
        assert resp.status_code == 404

    def test_recancel_returns_409(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        client.post(
            f"/api/v1/reservations/{created['id']}/cancel", headers=admin_headers
        )
        resp = client.post(
            f"/api/v1/reservations/{created['id']}/cancel", headers=admin_headers
        )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "La reserva ya se encuentra cancelada"

    def test_edit_cancelled_returns_409(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        client.post(
            f"/api/v1/reservations/{created['id']}/cancel", headers=admin_headers
        )
        resp = client.patch(
            f"/api/v1/reservations/{created['id']}",
            json={"check_out_date": "2026-09-10"},
            headers=admin_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Una reserva cancelada no puede ser modificada"

    def test_cancelled_range_can_be_rebooked(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        client.post(
            f"/api/v1/reservations/{created['id']}/cancel", headers=admin_headers
        )
        # Same range is now free
        resp = client.post("/api/v1/reservations/", json=_body(), headers=admin_headers)
        assert resp.status_code == 201


class TestNoDeleteEndpoint:
    def test_delete_not_allowed(self, client, admin_headers):
        created = client.post(
            "/api/v1/reservations/", json=_body(), headers=admin_headers
        ).json()
        resp = client.delete(
            f"/api/v1/reservations/{created['id']}", headers=admin_headers
        )
        assert resp.status_code == 405
