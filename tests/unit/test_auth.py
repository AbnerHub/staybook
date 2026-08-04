"""Unit tests for app.core.auth module."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.core.auth import get_current_admin_user, get_current_user
from app.core.config import settings


def _make_token(payload: dict, secret: str | None = None, algorithm: str | None = None) -> str:
    """Helper to create JWT tokens for testing."""
    return jwt.encode(
        payload,
        secret or settings.secret_key,
        algorithm=algorithm or settings.jwt_algorithm,
    )


def _make_credentials(token: str) -> HTTPAuthorizationCredentials:
    """Helper to wrap a token string in HTTPAuthorizationCredentials."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    def test_valid_token_returns_user_dict(self):
        payload = {"sub": "user123", "role": "admin"}
        token = _make_token(payload)
        credentials = _make_credentials(token)

        result = get_current_user(credentials)

        assert result["sub"] == "user123"
        assert result["role"] == "admin"

    def test_valid_token_without_role_defaults_to_empty_string(self):
        payload = {"sub": "user456"}
        token = _make_token(payload)
        credentials = _make_credentials(token)

        result = get_current_user(credentials)

        assert result["sub"] == "user456"
        assert result["role"] == ""

    def test_expired_token_raises_401(self):
        payload = {
            "sub": "user789",
            "role": "admin",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = _make_token(payload)
        credentials = _make_credentials(token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "expirado" in exc_info.value.detail.lower()

    def test_invalid_signature_raises_401(self):
        payload = {"sub": "user000", "role": "admin"}
        token = _make_token(payload, secret="wrong-secret-key")
        credentials = _make_credentials(token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "inválido" in exc_info.value.detail.lower()

    def test_malformed_token_raises_401(self):
        credentials = _make_credentials("not.a.valid.jwt.token")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials)

        assert exc_info.value.status_code == 401

    def test_token_without_sub_raises_401(self):
        payload = {"role": "admin"}
        token = _make_token(payload)
        credentials = _make_credentials(token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "sub" in exc_info.value.detail.lower()


class TestGetCurrentAdminUser:
    """Tests for get_current_admin_user dependency."""

    def test_admin_user_passes(self):
        user = {"sub": "admin1", "role": "admin"}

        result = get_current_admin_user(user)

        assert result == user

    def test_non_admin_role_raises_403(self):
        user = {"sub": "user1", "role": "staff"}

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin_user(user)

        assert exc_info.value.status_code == 403
        assert "permisos" in exc_info.value.detail.lower()

    def test_empty_role_raises_403(self):
        user = {"sub": "user2", "role": ""}

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin_user(user)

        assert exc_info.value.status_code == 403

    def test_missing_role_key_raises_403(self):
        user = {"sub": "user3"}

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin_user(user)

        assert exc_info.value.status_code == 403
