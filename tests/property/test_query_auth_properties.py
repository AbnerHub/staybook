# Feature: history-occupancy-availability-management, Property 12: Auth enforcement
"""
Property 12: Authentication and authorization enforcement for query endpoints.

Requests without a valid JWT → 401; valid JWT but non-admin role → 403.

**Validates: Requirements 9.1, 9.2, 9.3**
"""

import time

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from jose import jwt

from app.core.config import settings as app_settings
from app.main import app

client = TestClient(app)

ENDPOINTS = [
    "/api/v1/occupancy/current",
    "/api/v1/occupancy/rooms",
    "/api/v1/availability?check_in_date=2026-09-01&check_out_date=2026-09-05",
    "/api/v1/history/reservations",
]


def _create_token(payload: dict, secret: str | None = None) -> str:
    key = secret if secret is not None else app_settings.secret_key
    return jwt.encode(payload, key, algorithm=app_settings.jwt_algorithm)


random_token_strings = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=200,
)

non_admin_roles = st.sampled_from(
    ["user", "guest", "staff", "receptionist", "viewer", "manager", ""]
)

endpoint_strategy = st.sampled_from(ENDPOINTS)


@settings(max_examples=50)
@given(url=endpoint_strategy)
def test_no_auth_header_returns_401(url: str):
    assert client.get(url).status_code == 401


@settings(max_examples=50)
@given(url=endpoint_strategy, token=random_token_strings)
def test_malformed_token_returns_401(url: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get(url, headers=headers).status_code == 401


@settings(max_examples=50)
@given(url=endpoint_strategy)
def test_expired_token_returns_401(url: str):
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) - 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}
    assert client.get(url, headers=headers).status_code == 401


@settings(max_examples=50)
@given(url=endpoint_strategy, role=non_admin_roles)
def test_non_admin_role_returns_403(url: str, role: str):
    payload = {"sub": "regular_user", "role": role, "exp": int(time.time()) + 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}
    assert client.get(url, headers=headers).status_code == 403
