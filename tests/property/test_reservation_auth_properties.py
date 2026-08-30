# Feature: reservation-management, Property 10: Authentication and authorization
"""
Property 10: Authentication and authorization enforcement

For any request to the reservations module without a valid JWT token (missing,
expired, malformed, or wrong signature), the system shall return HTTP 401.
For any request with a valid JWT but without the admin role, the system shall
return HTTP 403. No reservation data shall be accessible or modifiable without
valid admin credentials.

**Validates: Requirements 11.1, 11.2, 11.3**
"""

import time

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from jose import jwt

from app.core.config import settings as app_settings
from app.main import app

client = TestClient(app)

# All reservation endpoints to test (no DELETE — reservations are preserved)
ENDPOINTS = [
    ("GET", "/api/v1/reservations"),
    ("GET", "/api/v1/reservations/1"),
    ("POST", "/api/v1/reservations"),
    ("PATCH", "/api/v1/reservations/1"),
    ("POST", "/api/v1/reservations/1/cancel"),
]

VALID_BODY = {
    "guest_id": 1,
    "room_id": 1,
    "check_in_date": "2026-09-01",
    "check_out_date": "2026-09-05",
}


def _make_request(method: str, url: str, headers: dict | None = None) -> int:
    kwargs: dict = {}
    if headers:
        kwargs["headers"] = headers
    if method == "POST" and url == "/api/v1/reservations":
        kwargs["json"] = VALID_BODY
    elif method == "PATCH":
        kwargs["json"] = {"check_out_date": "2026-09-06"}
    # /cancel POST has no body
    return client.request(method, url, **kwargs).status_code


def _create_token(payload: dict, secret: str | None = None) -> str:
    key = secret if secret is not None else app_settings.secret_key
    return jwt.encode(payload, key, algorithm=app_settings.jwt_algorithm)


# --- Strategies ---

random_token_strings = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=200,
)

non_admin_roles = st.sampled_from(
    ["user", "guest", "staff", "receptionist", "viewer", "manager", ""]
)

endpoint_strategy = st.sampled_from(ENDPOINTS)

RESERVATION_FIELDS = {
    "guest_id", "room_id", "check_in_date", "check_out_date",
    "status", "total_price", "created_at", "updated_at",
}


# --- Property Tests ---


@settings(max_examples=100)
@given(endpoint=endpoint_strategy)
def test_no_auth_header_returns_401(endpoint: tuple[str, str]):
    method, url = endpoint
    assert _make_request(method, url, headers=None) == 401


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, token=random_token_strings)
def test_malformed_token_returns_401(endpoint: tuple[str, str], token: str):
    method, url = endpoint
    headers = {"Authorization": f"Bearer {token}"}
    assert _make_request(method, url, headers=headers) == 401


@settings(max_examples=100)
@given(endpoint=endpoint_strategy)
def test_expired_token_returns_401(endpoint: tuple[str, str]):
    method, url = endpoint
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) - 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}
    assert _make_request(method, url, headers=headers) == 401


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, wrong_secret=st.text(min_size=10, max_size=50))
def test_wrong_signature_returns_401(endpoint: tuple[str, str], wrong_secret: str):
    method, url = endpoint
    if wrong_secret == app_settings.secret_key:
        wrong_secret = wrong_secret + "-different"
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) + 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload, secret=wrong_secret)}"}
    assert _make_request(method, url, headers=headers) == 401


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, role=non_admin_roles)
def test_non_admin_role_returns_403(endpoint: tuple[str, str], role: str):
    method, url = endpoint
    payload = {"sub": "regular_user", "role": role, "exp": int(time.time()) + 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}
    assert _make_request(method, url, headers=headers) == 403


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, role=non_admin_roles)
def test_no_reservation_data_in_non_admin_response(
    endpoint: tuple[str, str], role: str
):
    method, url = endpoint
    payload = {"sub": "regular_user", "role": role, "exp": int(time.time()) + 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}

    kwargs: dict = {"headers": headers}
    if method == "POST" and url == "/api/v1/reservations":
        kwargs["json"] = VALID_BODY
    elif method == "PATCH":
        kwargs["json"] = {"check_out_date": "2026-09-06"}

    body = client.request(method, url, **kwargs).json()

    if isinstance(body, dict):
        assert not RESERVATION_FIELDS.intersection(body.keys())
    elif isinstance(body, list):
        assert False, f"{method} {url} returned a list for non-admin user"


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, token=random_token_strings)
def test_no_reservation_data_in_unauthenticated_response(
    endpoint: tuple[str, str], token: str
):
    method, url = endpoint
    headers = {"Authorization": f"Bearer {token}"}

    kwargs: dict = {"headers": headers}
    if method == "POST" and url == "/api/v1/reservations":
        kwargs["json"] = VALID_BODY
    elif method == "PATCH":
        kwargs["json"] = {"check_out_date": "2026-09-06"}

    body = client.request(method, url, **kwargs).json()

    if isinstance(body, dict):
        assert not RESERVATION_FIELDS.intersection(body.keys())
    elif isinstance(body, list):
        assert False, f"{method} {url} returned a list for unauthenticated user"
