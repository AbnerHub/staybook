# Feature: room-management, Property 3: Invalid input rejection
"""
Property 3: Invalid input rejection

For any room data where at least one field violates validation rules
(price_per_night ≤ 0 or > 999999.99, capacity < 1 or > 20,
room_number > 10 characters), the system shall reject the operation
with a ValidationError.

**Validates: Requirements 1.3, 4.3**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.models.room import RoomStatus, RoomType
from app.schemas.room import RoomCreate


# --- Strategies ---

valid_room_number = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=10,
)

valid_room_type = st.sampled_from([e.value for e in RoomType])

valid_price = st.floats(min_value=0.01, max_value=999999.99, allow_nan=False)

valid_capacity = st.integers(min_value=1, max_value=20)

valid_status = st.sampled_from([e.value for e in RoomStatus])

# Invalid strategies
invalid_price = st.one_of(
    st.floats(max_value=0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=999999.995, allow_nan=False, allow_infinity=False),
)

invalid_capacity = st.one_of(
    st.integers(max_value=0),
    st.integers(min_value=21),
)

invalid_room_number = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=11,
    max_size=50,
)


# --- Property Tests ---


@settings(max_examples=100)
@given(price=invalid_price)
def test_invalid_price_rejected(price: float):
    """Room creation with price ≤ 0 or > 999999.99 raises ValidationError."""
    data = {
        "room_number": "101",
        "room_type": "individual",
        "price_per_night": price,
        "capacity": 5,
    }
    with pytest.raises(ValidationError):
        RoomCreate(**data)


@settings(max_examples=100)
@given(capacity=invalid_capacity)
def test_invalid_capacity_rejected(capacity: int):
    """Room creation with capacity < 1 or > 20 raises ValidationError."""
    data = {
        "room_number": "101",
        "room_type": "individual",
        "price_per_night": 100.0,
        "capacity": capacity,
    }
    with pytest.raises(ValidationError):
        RoomCreate(**data)


@settings(max_examples=100)
@given(room_number=invalid_room_number)
def test_invalid_room_number_rejected(room_number: str):
    """Room creation with room_number > 10 chars raises ValidationError."""
    data = {
        "room_number": room_number,
        "room_type": "individual",
        "price_per_night": 100.0,
        "capacity": 5,
    }
    with pytest.raises(ValidationError):
        RoomCreate(**data)


@settings(max_examples=100)
@given(
    price=invalid_price,
    capacity=invalid_capacity,
    room_number=invalid_room_number,
)
def test_multiple_invalid_fields_rejected(
    price: float, capacity: int, room_number: str
):
    """Room creation with multiple invalid fields raises ValidationError."""
    data = {
        "room_number": room_number,
        "room_type": "individual",
        "price_per_night": price,
        "capacity": capacity,
    }
    with pytest.raises(ValidationError):
        RoomCreate(**data)
