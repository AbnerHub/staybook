# Feature: guest-management, Property 7: Authentication and authorization enforcement
"""
Property 7: Authentication and authorization enforcement

For any request to the guests module without a valid JWT token (missing,
expired, malformed, or wrong signature), the system shall return HTTP 401.
For any request with a valid JWT but without the admin role, the system
shall return HTTP 403. No guest data shall be accessible or modifiable
without valid admin credentials.

**Validates: Requirements 8.1, 8.2, 8.3**
"""

import time

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from jose import jwt

from app.core.config import settings as app_settings
from app.main import app

client = TestClient(app)

# All guest endpoints to test (no DELETE — guests are preserved)
ENDPOINTS = [
    ("GET", "/api/v1/guests"),
    ("GET", "/api/v1/guests/1"),
    ("POST", "/api/v1/guests"),
    ("PATCH", "/api/v1/guests/1"),
]

VALID_BODY = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "5551234",
    "identification_type": "national_id",
    "identification_number": "X1234567",
}


def _make_request(method: str, url: str, headers: dict | None = None) -> int:
    kwargs: dict = {}
    if headers:
        kwargs["headers"] = headers
    if method == "POST":
        kwargs["json"] = VALID_BODY
    elif method == "PATCH":
        kwargs["json"] = {"phone": "5559999"}

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

GUEST_FIELDS = {
    "first_name", "last_name", "email", "phone",
    "identification_type", "identification_number",
    "created_at", "updated_at",
}


# --- Property Tests ---


@settings(max_examples=100)
@given(endpoint=endpoint_strategy)
def test_no_auth_header_returns_401(endpoint: tuple[str, str]):
    method, url = endpoint
    status_code = _make_request(method, url, headers=None)
    assert status_code == 401, (
        f"{method} {url} without auth returned {status_code}, expected 401"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, token=random_token_strings)
def test_malformed_token_returns_401(endpoint: tuple[str, str], token: str):
    method, url = endpoint
    headers = {"Authorization": f"Bearer {token}"}
    status_code = _make_request(method, url, headers=headers)
    assert status_code == 401, (
        f"{method} {url} with malformed token returned {status_code}, expected 401"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy)
def test_expired_token_returns_401(endpoint: tuple[str, str]):
    method, url = endpoint
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) - 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}
    status_code = _make_request(method, url, headers=headers)
    assert status_code == 401, (
        f"{method} {url} with expired token returned {status_code}, expected 401"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, wrong_secret=st.text(min_size=10, max_size=50))
def test_wrong_signature_returns_401(endpoint: tuple[str, str], wrong_secret: str):
    method, url = endpoint
    if wrong_secret == app_settings.secret_key:
        wrong_secret = wrong_secret + "-different"
    payload = {"sub": "admin_user", "role": "admin", "exp": int(time.time()) + 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload, secret=wrong_secret)}"}
    status_code = _make_request(method, url, headers=headers)
    assert status_code == 401, (
        f"{method} {url} with wrong-signature token returned "
        f"{status_code}, expected 401"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, role=non_admin_roles)
def test_non_admin_role_returns_403(endpoint: tuple[str, str], role: str):
    method, url = endpoint
    payload = {"sub": "regular_user", "role": role, "exp": int(time.time()) + 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}
    status_code = _make_request(method, url, headers=headers)
    assert status_code == 403, (
        f"{method} {url} with role='{role}' returned {status_code}, expected 403"
    )


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, role=non_admin_roles)
def test_no_guest_data_in_non_admin_response(endpoint: tuple[str, str], role: str):
    method, url = endpoint
    payload = {"sub": "regular_user", "role": role, "exp": int(time.time()) + 3600}
    headers = {"Authorization": f"Bearer {_create_token(payload)}"}

    kwargs: dict = {"headers": headers}
    if method == "POST":
        kwargs["json"] = VALID_BODY
    elif method == "PATCH":
        kwargs["json"] = {"phone": "5559999"}

    body = client.request(method, url, **kwargs).json()

    if isinstance(body, dict):
        assert not GUEST_FIELDS.intersection(body.keys()), (
            f"Response for non-admin contained guest data: "
            f"{GUEST_FIELDS.intersection(body.keys())}"
        )
    elif isinstance(body, list):
        assert False, f"{method} {url} returned a list for non-admin user"


@settings(max_examples=100)
@given(endpoint=endpoint_strategy, token=random_token_strings)
def test_no_guest_data_in_unauthenticated_response(
    endpoint: tuple[str, str], token: str
):
    method, url = endpoint
    headers = {"Authorization": f"Bearer {token}"}

    kwargs: dict = {"headers": headers}
    if method == "POST":
        kwargs["json"] = VALID_BODY
    elif method == "PATCH":
        kwargs["json"] = {"phone": "5559999"}

    body = client.request(method, url, **kwargs).json()

    if isinstance(body, dict):
        assert not GUEST_FIELDS.intersection(body.keys()), (
            f"Response for invalid token contained guest data: "
            f"{GUEST_FIELDS.intersection(body.keys())}"
        )
    elif isinstance(body, list):
        assert False, f"{method} {url} returned a list for unauthenticated user"
