# Feature: checkin-checkout-management, Property 10: Auth enforcement
"""
Property 10: Authentication and authorization enforcement for check-in/check-out.

Requests without a valid JWT → 401; valid JWT but non-admin role → 403.

**Validates: Requirements 10.1, 10.2, 10.3**
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
    ("POST", "/api/v1/reservations/1/check-in"),
    ("POST", "/api/v1/reservations/1/check-out"),
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
@given(endpoint=endpoint_strategy)
def test_no_auth_header_returns_401(endpoint: tuple[str, str]):
    method, url = endpoint
    assert client.request(method, url).status_code == 401


@settings(max_examples=50)
@given(endpoint=endpoint_strategy, token=random_token_strings)
def test_malformed_token_returns_401(endpoint: tuple[str, str], token: str):
    method, url = endpoint
    headers = {"Authorization": f"Bearer {token}"}
    assert client.request(method, url, headers=headers).status_code == 401


@settings(max_examples=50)
@given(endpoint=endpoint_strategy)
def test_expired_token_returns_401(endpoint: tuple[str, str]):
    method, url = endpoint
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) - 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}
    assert client.request(method, url, headers=headers).status_code == 401


@settings(max_examples=50)
@given(endpoint=endpoint_strategy, role=non_admin_roles)
def test_non_admin_role_returns_403(endpoint: tuple[str, str], role: str):
    method, url = endpoint
    payload = {"sub": "regular_user", "role": role, "exp": int(time.time()) + 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}
    assert client.request(method, url, headers=headers).status_code == 403
