# Feature: room-management, Property 1: Room creation round-trip
# Feature: room-management, Property 2: Duplicate room number rejection
"""
Property 1: Room creation round-trip

For any valid room data (room_number ≤ 10 chars, room_type ∈ {individual, doble, suite},
price ∈ [0.01, 999999.99], capacity ∈ [1, 20]), creating a room and then retrieving it
by ID should return a room with all the same field values provided at creation time,
with status defaulting to "disponible" when not explicitly set.

**Validates: Requirements 1.1, 6.1**

Property 2: Duplicate room number rejection

For any two room creation or update attempts that result in the same room_number
value, the system shall reject the second operation regardless of other field values.
The first room remains unchanged.

**Validates: Requirements 1.2, 4.4**
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import RoomDuplicateException, RoomOccupiedException
from app.db.base import Base
from app.models.room import RoomStatus, RoomType
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomCreate, RoomUpdate
from app.services.room_service import RoomService


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

optional_description = st.one_of(st.none(), st.text(max_size=255))

optional_floor = st.one_of(st.none(), st.integers(min_value=-5, max_value=100))


# --- Helper ---


def create_session():
    """Create a fresh in-memory SQLite session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


# --- Property Tests ---


@settings(max_examples=100)
@given(
    room_number=valid_room_number,
    room_type=valid_room_type,
    price_per_night=valid_price,
    capacity=valid_capacity,
    status=valid_status,
    description=optional_description,
    floor=optional_floor,
)
def test_room_creation_round_trip_all_fields_match(
    room_number: str,
    room_type: str,
    price_per_night: float,
    capacity: int,
    status: str,
    description: str | None,
    floor: int | None,
):
    """
    For any valid room data, create then retrieve by ID → all fields match.

    **Validates: Requirements 1.1, 6.1**
    """
    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    room_data = RoomCreate(
        room_number=room_number,
        room_type=room_type,
        price_per_night=price_per_night,
        capacity=capacity,
        status=status,
        description=description,
        floor=floor,
    )

    created_room = service.create_room(room_data)
    retrieved_room = service.get_room(created_room.id)

    # All fields must match
    assert retrieved_room.room_number == room_number
    assert retrieved_room.room_type.value == room_type
    assert float(retrieved_room.price_per_night) == float(
        Decimal(str(price_per_night)).quantize(Decimal("0.01"))
    )
    assert retrieved_room.capacity == capacity
    assert retrieved_room.status.value == status
    assert retrieved_room.description == description
    assert retrieved_room.floor == floor
    assert retrieved_room.id is not None
    assert retrieved_room.created_at is not None
    assert retrieved_room.updated_at is not None

    session.close()


@settings(max_examples=100)
@given(
    room_number=valid_room_number,
    room_type=valid_room_type,
    price_per_night=valid_price,
    capacity=valid_capacity,
    description=optional_description,
    floor=optional_floor,
)
def test_room_creation_defaults_status_to_disponible(
    room_number: str,
    room_type: str,
    price_per_night: float,
    capacity: int,
    description: str | None,
    floor: int | None,
):
    """
    When status is not explicitly set, it defaults to "disponible".

    **Validates: Requirements 1.1, 6.1**
    """
    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    # Create without explicitly setting status (uses default)
    room_data = RoomCreate(
        room_number=room_number,
        room_type=room_type,
        price_per_night=price_per_night,
        capacity=capacity,
        description=description,
        floor=floor,
    )

    created_room = service.create_room(room_data)
    retrieved_room = service.get_room(created_room.id)

    # Status must default to "disponible"
    assert retrieved_room.status == RoomStatus.DISPONIBLE
    assert retrieved_room.status.value == "disponible"

    session.close()



# --- Property 2: Duplicate room number rejection ---


@settings(max_examples=100)
@given(
    room_number=valid_room_number,
    room_type1=valid_room_type,
    price1=valid_price,
    capacity1=valid_capacity,
    status1=valid_status,
    description1=optional_description,
    floor1=optional_floor,
    room_type2=valid_room_type,
    price2=valid_price,
    capacity2=valid_capacity,
)
def test_duplicate_room_number_on_create_is_rejected(
    room_number: str,
    room_type1: str,
    price1: float,
    capacity1: int,
    status1: str,
    description1: str | None,
    floor1: int | None,
    room_type2: str,
    price2: float,
    capacity2: int,
):
    """
    Creating two rooms with the same room_number should reject the second
    and leave the first unchanged.

    **Validates: Requirements 1.2**
    """
    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    # Create the first room
    first_data = RoomCreate(
        room_number=room_number,
        room_type=room_type1,
        price_per_night=price1,
        capacity=capacity1,
        status=status1,
        description=description1,
        floor=floor1,
    )
    first_room = service.create_room(first_data)

    # Store original values for comparison
    original_id = first_room.id
    original_room_number = first_room.room_number
    original_room_type = first_room.room_type
    original_price = float(first_room.price_per_night)
    original_capacity = first_room.capacity
    original_status = first_room.status
    original_description = first_room.description
    original_floor = first_room.floor

    # Attempt to create a second room with the same room_number
    second_data = RoomCreate(
        room_number=room_number,
        room_type=room_type2,
        price_per_night=price2,
        capacity=capacity2,
    )

    with pytest.raises(RoomDuplicateException):
        service.create_room(second_data)

    # Verify the first room remains unchanged
    retrieved = service.get_room(original_id)
    assert retrieved.room_number == original_room_number
    assert retrieved.room_type == original_room_type
    assert float(retrieved.price_per_night) == original_price
    assert retrieved.capacity == original_capacity
    assert retrieved.status == original_status
    assert retrieved.description == original_description
    assert retrieved.floor == original_floor

    session.close()


@settings(max_examples=100)
@given(
    room_number1=valid_room_number,
    room_number2=valid_room_number,
    room_type1=valid_room_type,
    price1=valid_price,
    capacity1=valid_capacity,
    room_type2=valid_room_type,
    price2=valid_price,
    capacity2=valid_capacity,
)
def test_update_room_number_to_existing_is_rejected(
    room_number1: str,
    room_number2: str,
    room_type1: str,
    price1: float,
    capacity1: int,
    room_type2: str,
    price2: float,
    capacity2: int,
):
    """
    Updating a room's room_number to one that already exists in another room
    should be rejected, and the first room remains unchanged.

    **Validates: Requirements 4.4**
    """
    # Ensure the two rooms have different room_numbers
    assume(room_number1 != room_number2)

    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    # Create both rooms
    room1_data = RoomCreate(
        room_number=room_number1,
        room_type=room_type1,
        price_per_night=price1,
        capacity=capacity1,
    )
    room1 = service.create_room(room1_data)

    room2_data = RoomCreate(
        room_number=room_number2,
        room_type=room_type2,
        price_per_night=price2,
        capacity=capacity2,
    )
    room2 = service.create_room(room2_data)

    # Store original values of room1 for comparison
    original_room1_number = room1.room_number
    original_room1_type = room1.room_type
    original_room1_price = float(room1.price_per_night)
    original_room1_capacity = room1.capacity
    original_room1_status = room1.status

    # Try to update room2's room_number to room1's room_number
    update_data = RoomUpdate(room_number=room1.room_number)

    with pytest.raises(RoomDuplicateException):
        service.update_room(room2.id, update_data)

    # Verify room1 remains unchanged
    retrieved_room1 = service.get_room(room1.id)
    assert retrieved_room1.room_number == original_room1_number
    assert retrieved_room1.room_type == original_room1_type
    assert float(retrieved_room1.price_per_night) == original_room1_price
    assert retrieved_room1.capacity == original_room1_capacity
    assert retrieved_room1.status == original_room1_status

    # Verify room2's room_number was NOT changed
    retrieved_room2 = service.get_room(room2.id)
    assert retrieved_room2.room_number == room_number2

    session.close()


# --- Property 4: Availability filter correctness ---
# Feature: room-management, Property 4: Availability filter correctness


@settings(max_examples=100)
@given(
    rooms_data=st.lists(
        st.fixed_dictionaries(
            {
                "room_type": st.sampled_from([e.value for e in RoomType]),
                "price_per_night": st.floats(
                    min_value=0.01, max_value=999999.99, allow_nan=False
                ),
                "capacity": st.integers(min_value=1, max_value=20),
                "status": st.sampled_from([e.value for e in RoomStatus]),
            }
        ),
        min_size=0,
        max_size=20,
    )
)
def test_availability_filter_returns_exactly_disponible_rooms(rooms_data):
    """
    Insert rooms with mixed statuses → list_available_rooms returns exactly
    rooms with status 'disponible'. No room with 'ocupada' or 'mantenimiento'
    should appear; no 'disponible' room should be absent.

    **Validates: Requirements 3.1, 3.2**
    """
    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    # Insert rooms with unique room_numbers
    for i, data in enumerate(rooms_data):
        room_create = RoomCreate(
            room_number=f"R{i:04d}",
            room_type=data["room_type"],
            price_per_night=data["price_per_night"],
            capacity=data["capacity"],
            status=data["status"],
        )
        service.create_room(room_create)

    # Call the service method under test
    available_rooms = service.list_available_rooms()

    # Determine expected count (rooms with status "disponible")
    expected_count = sum(
        1 for d in rooms_data if d["status"] == RoomStatus.DISPONIBLE.value
    )

    # Verify count matches exactly
    assert len(available_rooms) == expected_count, (
        f"Expected {expected_count} available rooms, got {len(available_rooms)}"
    )

    # Verify all returned rooms have status "disponible"
    for room in available_rooms:
        assert room.status == RoomStatus.DISPONIBLE, (
            f"Room {room.room_number} has status '{room.status.value}' "
            f"but should be 'disponible'"
        )

    # Verify no "disponible" room is missing from the result
    available_room_numbers = {r.room_number for r in available_rooms}
    for i, data in enumerate(rooms_data):
        if data["status"] == RoomStatus.DISPONIBLE.value:
            room_number = f"R{i:04d}"
            assert room_number in available_room_numbers, (
                f"Room {room_number} with status 'disponible' "
                f"is missing from available rooms list"
            )

    # Verify no "ocupada" or "mantenimiento" room is in the result
    for room in available_rooms:
        assert room.status != RoomStatus.OCUPADA, (
            f"Room {room.room_number} with status 'ocupada' "
            f"should not appear in available rooms"
        )
        assert room.status != RoomStatus.MANTENIMIENTO, (
            f"Room {room.room_number} with status 'mantenimiento' "
            f"should not appear in available rooms"
        )

    session.close()


# --- Property 6: Deletion rules by room status ---
# Feature: room-management, Property 6: Deletion rules by room status


@settings(max_examples=100)
@given(
    room_number=valid_room_number,
    room_type=valid_room_type,
    price_per_night=valid_price,
    capacity=valid_capacity,
    status=st.sampled_from([RoomStatus.DISPONIBLE.value, RoomStatus.MANTENIMIENTO.value]),
)
def test_deletion_succeeds_for_non_occupied_rooms(
    room_number: str,
    room_type: str,
    price_per_night: float,
    capacity: int,
    status: str,
):
    """
    Rooms with status 'disponible' or 'mantenimiento' can be deleted.

    **Validates: Requirements 5.1, 5.4**
    """
    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    room_data = RoomCreate(
        room_number=room_number,
        room_type=room_type,
        price_per_night=price_per_night,
        capacity=capacity,
        status=status,
    )
    created_room = service.create_room(room_data)
    room_id = created_room.id

    # Deletion should succeed
    service.delete_room(room_id)

    # Room should no longer exist
    assert repository.get_by_id(room_id) is None

    session.close()


@settings(max_examples=100)
@given(
    room_number=valid_room_number,
    room_type=valid_room_type,
    price_per_night=valid_price,
    capacity=valid_capacity,
)
def test_deletion_fails_for_occupied_rooms(
    room_number: str,
    room_type: str,
    price_per_night: float,
    capacity: int,
):
    """
    Rooms with status 'ocupada' cannot be deleted — raises RoomOccupiedException.

    **Validates: Requirements 5.3**
    """
    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    room_data = RoomCreate(
        room_number=room_number,
        room_type=room_type,
        price_per_night=price_per_night,
        capacity=capacity,
        status=RoomStatus.OCUPADA.value,
    )
    created_room = service.create_room(room_data)
    room_id = created_room.id

    # Deletion should raise RoomOccupiedException
    with pytest.raises(RoomOccupiedException):
        service.delete_room(room_id)

    # Room should still exist
    assert repository.get_by_id(room_id) is not None

    session.close()


@settings(max_examples=100)
@given(
    room_number=valid_room_number,
    room_type=valid_room_type,
    price_per_night=valid_price,
    capacity=valid_capacity,
    status=valid_status,
)
def test_deletion_succeeds_iff_status_not_occupied(
    room_number: str,
    room_type: str,
    price_per_night: float,
    capacity: int,
    status: str,
):
    """
    Deletion succeeds iff status != 'ocupada'. This is the complete biconditional
    property covering all three statuses in a single test.

    **Validates: Requirements 5.1, 5.3, 5.4**
    """
    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    room_data = RoomCreate(
        room_number=room_number,
        room_type=room_type,
        price_per_night=price_per_night,
        capacity=capacity,
        status=status,
    )
    created_room = service.create_room(room_data)
    room_id = created_room.id

    if status == RoomStatus.OCUPADA.value:
        with pytest.raises(RoomOccupiedException):
            service.delete_room(room_id)
        # Room still exists after failed deletion
        assert repository.get_by_id(room_id) is not None
    else:
        service.delete_room(room_id)
        # Room removed after successful deletion
        assert repository.get_by_id(room_id) is None

    session.close()


# Feature: room-management, Property 5: Partial update field preservation

# --- Property 5: Partial update field preservation ---


# Strategy that generates a non-empty subset of updatable field names
UPDATABLE_FIELDS = [
    "room_number",
    "room_type",
    "price_per_night",
    "capacity",
    "status",
    "description",
    "floor",
]


def valid_value_for_field(field_name: str):
    """Return a Hypothesis strategy that generates valid values for a given field."""
    if field_name == "room_number":
        return st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=10,
        )
    elif field_name == "room_type":
        return st.sampled_from([e.value for e in RoomType])
    elif field_name == "price_per_night":
        return st.floats(min_value=0.01, max_value=999999.99, allow_nan=False)
    elif field_name == "capacity":
        return st.integers(min_value=1, max_value=20)
    elif field_name == "status":
        return st.sampled_from([e.value for e in RoomStatus])
    elif field_name == "description":
        return st.one_of(st.none(), st.text(max_size=255))
    elif field_name == "floor":
        return st.one_of(st.none(), st.integers(min_value=-5, max_value=100))
    else:
        raise ValueError(f"Unknown field: {field_name}")


@st.composite
def partial_update_strategy(draw):
    """
    Generate a non-empty subset of updatable fields with valid new values.
    Returns a dict of {field_name: new_value}.
    """
    # Pick a non-empty subset of fields to update
    subset = draw(
        st.lists(
            st.sampled_from(UPDATABLE_FIELDS),
            min_size=1,
            max_size=len(UPDATABLE_FIELDS),
            unique=True,
        )
    )
    update_values = {}
    for field in subset:
        update_values[field] = draw(valid_value_for_field(field))
    return update_values


@settings(max_examples=100)
@given(
    room_number=valid_room_number,
    room_type=valid_room_type,
    price_per_night=valid_price,
    capacity=valid_capacity,
    status=valid_status,
    description=optional_description,
    floor=optional_floor,
    update_fields=partial_update_strategy(),
)
def test_partial_update_field_preservation(
    room_number: str,
    room_type: str,
    price_per_night: float,
    capacity: int,
    status: str,
    description: str | None,
    floor: int | None,
    update_fields: dict,
):
    """
    For any room and any subset of fields, update only those fields →
    other fields remain unchanged.

    **Validates: Requirements 4.1**
    """
    # If update_fields contains a room_number, ensure it differs from original
    # to avoid false negatives on duplicate checks
    if "room_number" in update_fields:
        assume(update_fields["room_number"] != room_number)

    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    # Create the room with initial values
    room_data = RoomCreate(
        room_number=room_number,
        room_type=room_type,
        price_per_night=price_per_night,
        capacity=capacity,
        status=status,
        description=description,
        floor=floor,
    )
    created_room = service.create_room(room_data)
    room_id = created_room.id

    # Capture the original values before update
    original_values = {
        "room_number": created_room.room_number,
        "room_type": created_room.room_type.value,
        "price_per_night": float(created_room.price_per_night),
        "capacity": created_room.capacity,
        "status": created_room.status.value,
        "description": created_room.description,
        "floor": created_room.floor,
    }

    # Apply partial update with only the selected fields
    update_data = RoomUpdate(**update_fields)
    updated_room = service.update_room(room_id, update_data)

    # Verify: updated fields match the new values
    for field, new_value in update_fields.items():
        actual = getattr(updated_room, field)
        if field in ("room_type", "status"):
            # Enum fields: compare by value
            assert actual.value == new_value, (
                f"Updated field '{field}' expected {new_value}, got {actual.value}"
            )
        elif field == "price_per_night":
            # Decimal comparison
            assert float(actual) == float(
                Decimal(str(new_value)).quantize(Decimal("0.01"))
            ), f"Updated field '{field}' expected {new_value}, got {float(actual)}"
        else:
            assert actual == new_value, (
                f"Updated field '{field}' expected {new_value}, got {actual}"
            )

    # Verify: non-updated fields remain at their previous values
    for field in UPDATABLE_FIELDS:
        if field in update_fields:
            continue  # Already verified above
        actual = getattr(updated_room, field)
        expected = original_values[field]
        if field in ("room_type", "status"):
            assert actual.value == expected, (
                f"Preserved field '{field}' expected {expected}, got {actual.value}"
            )
        elif field == "price_per_night":
            assert float(actual) == expected, (
                f"Preserved field '{field}' expected {expected}, got {float(actual)}"
            )
        else:
            assert actual == expected, (
                f"Preserved field '{field}' expected {expected}, got {actual}"
            )

    session.close()


# --- Property 7: List completeness invariant ---
# Feature: room-management, Property 7: List completeness invariant


@settings(max_examples=100)
@given(
    rooms_data=st.lists(
        st.fixed_dictionaries(
            {
                "room_type": st.sampled_from([e.value for e in RoomType]),
                "price_per_night": st.floats(
                    min_value=0.01, max_value=999999.99, allow_nan=False
                ),
                "capacity": st.integers(min_value=1, max_value=20),
                "status": st.sampled_from([e.value for e in RoomStatus]),
                "description": st.one_of(st.none(), st.text(max_size=255)),
                "floor": st.one_of(
                    st.none(), st.integers(min_value=-5, max_value=100)
                ),
            }
        ),
        min_size=0,
        max_size=20,
    )
)
def test_list_completeness_invariant(rooms_data):
    """
    For N inserted rooms, list_rooms returns exactly N rooms with all
    attributes intact.

    **Validates: Requirements 2.1**
    """
    session = create_session()
    repository = RoomRepository(db=session)
    service = RoomService(repository=repository)

    # Insert N rooms with unique room_numbers
    inserted = []
    for i, data in enumerate(rooms_data):
        room_create = RoomCreate(
            room_number=f"L{i:04d}",
            room_type=data["room_type"],
            price_per_night=data["price_per_night"],
            capacity=data["capacity"],
            status=data["status"],
            description=data["description"],
            floor=data["floor"],
        )
        created = service.create_room(room_create)
        inserted.append(created)

    # Call list_rooms
    listed_rooms = service.list_rooms()

    # Verify: result contains exactly N rooms
    assert len(listed_rooms) == len(rooms_data), (
        f"Expected {len(rooms_data)} rooms, got {len(listed_rooms)}"
    )

    # Build a lookup by room_number for verification
    listed_by_number = {r.room_number: r for r in listed_rooms}

    # Verify: every inserted room is present and all attributes are intact
    for i, data in enumerate(rooms_data):
        room_number = f"L{i:04d}"
        assert room_number in listed_by_number, (
            f"Room '{room_number}' not found in list_rooms result"
        )

        room = listed_by_number[room_number]

        # Verify all attributes match what was inserted
        assert room.room_type.value == data["room_type"], (
            f"Room '{room_number}' room_type mismatch: "
            f"expected '{data['room_type']}', got '{room.room_type.value}'"
        )
        expected_price = float(
            Decimal(str(data["price_per_night"])).quantize(Decimal("0.01"))
        )
        assert float(room.price_per_night) == expected_price, (
            f"Room '{room_number}' price_per_night mismatch: "
            f"expected {expected_price}, got {float(room.price_per_night)}"
        )
        assert room.capacity == data["capacity"], (
            f"Room '{room_number}' capacity mismatch: "
            f"expected {data['capacity']}, got {room.capacity}"
        )
        assert room.status.value == data["status"], (
            f"Room '{room_number}' status mismatch: "
            f"expected '{data['status']}', got '{room.status.value}'"
        )
        assert room.description == data["description"], (
            f"Room '{room_number}' description mismatch: "
            f"expected '{data['description']}', got '{room.description}'"
        )
        assert room.floor == data["floor"], (
            f"Room '{room_number}' floor mismatch: "
            f"expected {data['floor']}, got {room.floor}"
        )
        assert room.id is not None
        assert room.created_at is not None
        assert room.updated_at is not None

    session.close()
