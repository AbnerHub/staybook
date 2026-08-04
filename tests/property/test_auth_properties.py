# Feature: room-management, Property 8: Authentication and authorization enforcement
"""
Property 8: Authentication and authorization enforcement

For any request to the rooms module without a valid JWT token (missing,
expired, malformed, or wrong signature), the system shall return HTTP 401.
For any request with a valid JWT but without the admin role, the system
shall return HTTP 403. No room data shall be accessible or modifiable
without valid admin credentials.

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

# All room endpoints to test
ENDPOINTS = [
    ("GET", "/api/v1/rooms"),
    ("GET", "/api/v1/rooms/available"),
    ("GET", "/api/v1/rooms/1"),
    ("POST", "/api/v1/rooms"),
    ("PATCH", "/api/v1/rooms/1"),
    ("DELETE", "/api/v1/rooms/1"),
]


def _make_request(method: str, url: str, headers: dict | None = None) -> int:
    """Execute a request and return the status code."""
    kwargs: dict = {}
    if headers:
        kwargs["headers"] = headers
    if method == "POST":
        kwargs["json"] = {
            "room_number": "101",
            "room_type": "individual",
            "price_per_night": 100.0,
            "capacity": 2,
        }
    elif method == "PATCH":
        kwargs["json"] = {"price_per_night": 150.0}

    response = client.request(method, url, **kwargs)
    return response.status_code


def _create_token(payload: dict, secret: str | None = None) -> str:
    """Create a JWT token with the given payload."""
    key = secret if secret is not None else app_settings.secret_key
    return jwt.encode(payload, key, algorithm=app_settings.jwt_algorithm)


# --- Strategies ---

# Random strings that are NOT valid JWTs (ASCII-only for HTTP headers)
random_token_strings = st.text(
    alphabet=st.characters(
        min_codepoint=33, max_codepoint=126,
    ),
    min_size=1,
    max_size=200,
)

# Non-admin roles
non_admin_roles = st.sampled_from(
    ["user", "guest", "staff", "receptionist", "viewer", "manager", ""]
)

# Strategy for endpoint selection
endpoint_strategy = st.sampled_from(ENDPOINTS)


# --- Property Tests ---


@settings(max_examples=100)
@given(endpoint=endpoint_strategy)
def test_no_auth_header_returns_401(endpoint: tuple[str, str]):
    """Requests without Authorization header return 401 for all endpoints."""
    method, url = endpoint
    status_code = _make_request(method, url, headers=None)
    assert status_code == 401, (
        f"{method} {url} without auth returned {status_code}, expected 401"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, token=random_token_strings)
def test_malformed_token_returns_401(
    endpoint: tuple[str, str], token: str
):
    """Requests with random/malformed tokens return 401 for all endpoints."""
    method, url = endpoint
    headers = {"Authorization": f"Bearer {token}"}
    status_code = _make_request(method, url, headers=headers)
    assert status_code == 401, (
        f"{method} {url} with malformed token returned {status_code}, expected 401"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy)
def test_expired_token_returns_401(endpoint: tuple[str, str]):
    """Requests with an expired JWT return 401 for all endpoints."""
    method, url = endpoint
    payload = {
        "sub": "admin_user",
        "role": "admin",
        "exp": int(time.time()) - 3600,  # Expired 1 hour ago
    }
    token = _create_token(payload)
    headers = {"Authorization": f"Bearer {token}"}
    status_code = _make_request(method, url, headers=headers)
    assert status_code == 401, (
        f"{method} {url} with expired token returned {status_code}, expected 401"
    )


@settings(max_examples=100)
@given(
    endpoint=endpoint_strategy,
    wrong_secret=st.text(min_size=10, max_size=50),
)
def test_wrong_signature_returns_401(
    endpoint: tuple[str, str], wrong_secret: str
):
    """Requests with JWT signed by wrong key return 401 for all endpoints."""
    method, url = endpoint
    # Ensure the wrong secret differs from the real one
    if wrong_secret == app_settings.secret_key:
        wrong_secret = wrong_secret + "-different"

    payload = {
        "sub": "admin_user",
        "role": "admin",
        "exp": int(time.time()) + 3600,
    }
    token = _create_token(payload, secret=wrong_secret)
    headers = {"Authorization": f"Bearer {token}"}
    status_code = _make_request(method, url, headers=headers)
    assert status_code == 401, (
        f"{method} {url} with wrong-signature token returned "
        f"{status_code}, expected 401"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, role=non_admin_roles)
def test_non_admin_role_returns_403(
    endpoint: tuple[str, str], role: str
):
    """Requests with valid JWT but non-admin role return 403."""
    method, url = endpoint
    payload = {
        "sub": "regular_user",
        "role": role,
        "exp": int(time.time()) + 3600,
    }
    token = _create_token(payload)
    headers = {"Authorization": f"Bearer {token}"}
    status_code = _make_request(method, url, headers=headers)
    assert status_code == 403, (
        f"{method} {url} with role='{role}' returned {status_code}, expected 403"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, role=non_admin_roles)
def test_no_room_data_in_non_admin_response(
    endpoint: tuple[str, str], role: str
):
    """Non-admin responses never contain room data fields."""
    method, url = endpoint
    payload = {
        "sub": "regular_user",
        "role": role,
        "exp": int(time.time()) + 3600,
    }
    token = _create_token(payload)
    headers = {"Authorization": f"Bearer {token}"}

    kwargs: dict = {"headers": headers}
    if method == "POST":
        kwargs["json"] = {
            "room_number": "101",
            "room_type": "individual",
            "price_per_night": 100.0,
            "capacity": 2,
        }
    elif method == "PATCH":
        kwargs["json"] = {"price_per_night": 150.0}

    response = client.request(method, url, **kwargs)
    body = response.json()

    # Room data fields that should NEVER appear in unauthorized responses
    room_fields = {
        "room_number", "room_type", "price_per_night",
        "capacity", "status", "floor", "created_at", "updated_at",
    }

    if isinstance(body, dict):
        assert not room_fields.intersection(body.keys()), (
            f"Response for non-admin contained room data: "
            f"{room_fields.intersection(body.keys())}"
        )
    elif isinstance(body, list):
        # Should never get a list back without admin access
        assert False, (
            f"{method} {url} returned a list for non-admin user"
        )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, token=random_token_strings)
def test_no_room_data_in_unauthenticated_response(
    endpoint: tuple[str, str], token: str
):
    """Unauthenticated responses never contain room data fields."""
    method, url = endpoint
    headers = {"Authorization": f"Bearer {token}"}

    kwargs: dict = {"headers": headers}
    if method == "POST":
        kwargs["json"] = {
            "room_number": "101",
            "room_type": "individual",
            "price_per_night": 100.0,
            "capacity": 2,
        }
    elif method == "PATCH":
        kwargs["json"] = {"price_per_night": 150.0}

    response = client.request(method, url, **kwargs)
    body = response.json()

    room_fields = {
        "room_number", "room_type", "price_per_night",
        "capacity", "status", "floor", "created_at", "updated_at",
    }

    if isinstance(body, dict):
        assert not room_fields.intersection(body.keys()), (
            f"Response for invalid token contained room data: "
            f"{room_fields.intersection(body.keys())}"
        )
    elif isinstance(body, list):
        assert False, (
            f"{method} {url} returned a list for unauthenticated user"
        )
