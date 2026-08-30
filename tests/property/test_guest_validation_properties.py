# Feature: guest-management, Property 4: Invalid input rejection
"""
Property 4: Invalid input rejection

For any guest data where at least one field violates validation rules
(empty/over-length first_name or last_name, invalid/over-length email,
phone outside 7-20 chars, empty/over-length identification_number,
identification_type outside the allowed enum), the system shall reject
the operation with a ValidationError and not persist any data.

**Validates: Requirements 1.4, 4.3**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.schemas.guest import GuestCreate

# --- Valid baseline ---

VALID_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "555-1234",
    "identification_type": "national_id",
    "identification_number": "X1234567",
}

# --- Invalid strategies ---

# Names: empty, whitespace-only, or longer than 100 chars
invalid_name = st.one_of(
    st.just(""),
    st.just("   "),
    st.text(min_size=101, max_size=200),
)

# Emails without a valid format
invalid_email = st.sampled_from(
    ["", "not-an-email", "missing@", "@missing.com", "a b@c.com", "plainaddress"]
)

# Phone: too short (<7) or too long (>20)
invalid_phone = st.one_of(
    st.text(alphabet="0123456789", min_size=0, max_size=6),
    st.text(alphabet="0123456789", min_size=21, max_size=40),
)

# Identification number: empty, whitespace-only, or > 50 chars
invalid_identification_number = st.one_of(
    st.just(""),
    st.just("   "),
    st.text(min_size=51, max_size=100),
)

# Identification type outside the enum
invalid_identification_type = st.sampled_from(
    ["dni", "pasaporte", "licencia", "", "unknown"]
)


# --- Property Tests ---


@settings(max_examples=100)
@given(first_name=invalid_name)
def test_invalid_first_name_rejected(first_name: str):
    with pytest.raises(ValidationError):
        GuestCreate(**{**VALID_DATA, "first_name": first_name})


@settings(max_examples=100)
@given(last_name=invalid_name)
def test_invalid_last_name_rejected(last_name: str):
    with pytest.raises(ValidationError):
        GuestCreate(**{**VALID_DATA, "last_name": last_name})


@settings(max_examples=100)
@given(email=invalid_email)
def test_invalid_email_rejected(email: str):
    with pytest.raises(ValidationError):
        GuestCreate(**{**VALID_DATA, "email": email})


@settings(max_examples=100)
@given(phone=invalid_phone)
def test_invalid_phone_rejected(phone: str):
    with pytest.raises(ValidationError):
        GuestCreate(**{**VALID_DATA, "phone": phone})


@settings(max_examples=100)
@given(identification_number=invalid_identification_number)
def test_invalid_identification_number_rejected(identification_number: str):
    with pytest.raises(ValidationError):
        GuestCreate(
            **{**VALID_DATA, "identification_number": identification_number}
        )


@settings(max_examples=100)
@given(identification_type=invalid_identification_type)
def test_invalid_identification_type_rejected(identification_type: str):
    with pytest.raises(ValidationError):
        GuestCreate(**{**VALID_DATA, "identification_type": identification_type})


def test_over_length_email_rejected():
    """Email longer than 255 chars is rejected."""
    long_local = "a" * 250
    with pytest.raises(ValidationError):
        GuestCreate(**{**VALID_DATA, "email": f"{long_local}@example.com"})
