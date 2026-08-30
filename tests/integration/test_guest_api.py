"""Integration tests for the Guest Management API endpoints.

Validates Requirements: 1.5, 2.2, 2.3, 3.1, 3.2, 4.2, 4.6, 7.2, 7.4, 7.5, 8.x
"""

import time

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


@pytest.fixture()
def client():
    """TestClient with an in-memory SQLite DB injected via get_db override."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

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


def _valid_body(**overrides) -> dict:
    body = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "5551234",
        "identification_type": "national_id",
        "identification_number": "X1234567",
    }
    body.update(overrides)
    return body


class TestCreateGuest:
    def test_create_returns_201_and_body(self, client, admin_headers):
        resp = client.post("/api/v1/guests/", json=_valid_body(), headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] is not None
        assert data["email"] == "john.doe@example.com"
        assert data["identification_type"] == "national_id"
        assert "created_at" in data and "updated_at" in data

    def test_duplicate_email_returns_409(self, client, admin_headers):
        client.post("/api/v1/guests/", json=_valid_body(), headers=admin_headers)
        resp = client.post(
            "/api/v1/guests/",
            json=_valid_body(identification_number="OTHER1"),
            headers=admin_headers,
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["detail"] == "El correo electrónico ya está registrado"
        assert body["status_code"] == 409

    def test_duplicate_identification_returns_409(self, client, admin_headers):
        client.post("/api/v1/guests/", json=_valid_body(), headers=admin_headers)
        resp = client.post(
            "/api/v1/guests/",
            json=_valid_body(email="other@example.com"),
            headers=admin_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "El documento de identificación ya está registrado"

    def test_invalid_body_returns_422(self, client, admin_headers):
        resp = client.post(
            "/api/v1/guests/",
            json=_valid_body(email="not-an-email"),
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestListGuests:
    def test_empty_list_returns_200(self, client, admin_headers):
        resp = client.get("/api/v1/guests/", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all_guests(self, client, admin_headers):
        client.post(
            "/api/v1/guests/",
            json=_valid_body(email="a@example.com", identification_number="1"),
            headers=admin_headers,
        )
        client.post(
            "/api/v1/guests/",
            json=_valid_body(email="b@example.com", identification_number="2"),
            headers=admin_headers,
        )
        resp = client.get("/api/v1/guests/", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetGuest:
    def test_returns_200_when_exists(self, client, admin_headers):
        created = client.post(
            "/api/v1/guests/", json=_valid_body(), headers=admin_headers
        ).json()
        resp = client.get(f"/api/v1/guests/{created['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_returns_404_when_not_found(self, client, admin_headers):
        resp = client.get("/api/v1/guests/999", headers=admin_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "El huésped no fue encontrado"

    def test_invalid_id_returns_422(self, client, admin_headers):
        resp = client.get("/api/v1/guests/abc", headers=admin_headers)
        assert resp.status_code == 422


class TestUpdateGuest:
    def test_partial_update_returns_200(self, client, admin_headers):
        created = client.post(
            "/api/v1/guests/", json=_valid_body(), headers=admin_headers
        ).json()
        resp = client.patch(
            f"/api/v1/guests/{created['id']}",
            json={"phone": "5559999"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone"] == "5559999"
        assert data["email"] == created["email"]
        assert data["id"] == created["id"]
        assert data["created_at"] == created["created_at"]

    def test_update_not_found_returns_404(self, client, admin_headers):
        resp = client.patch(
            "/api/v1/guests/999", json={"phone": "5559999"}, headers=admin_headers
        )
        assert resp.status_code == 404

    def test_update_email_to_existing_returns_409(self, client, admin_headers):
        client.post(
            "/api/v1/guests/",
            json=_valid_body(email="taken@example.com", identification_number="9"),
            headers=admin_headers,
        )
        created = client.post(
            "/api/v1/guests/", json=_valid_body(), headers=admin_headers
        ).json()
        resp = client.patch(
            f"/api/v1/guests/{created['id']}",
            json={"email": "taken@example.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 409

    def test_update_invalid_body_returns_422(self, client, admin_headers):
        created = client.post(
            "/api/v1/guests/", json=_valid_body(), headers=admin_headers
        ).json()
        resp = client.patch(
            f"/api/v1/guests/{created['id']}",
            json={"phone": "123"},  # too short
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestNoDeleteEndpoint:
    def test_delete_not_allowed(self, client, admin_headers):
        created = client.post(
            "/api/v1/guests/", json=_valid_body(), headers=admin_headers
        ).json()
        resp = client.delete(
            f"/api/v1/guests/{created['id']}", headers=admin_headers
        )
        # No DELETE route registered → 405 Method Not Allowed
        assert resp.status_code == 405
