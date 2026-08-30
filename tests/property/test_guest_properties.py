# Feature: guest-management
"""Property-based tests for GuestService.

Covers:
- Property 1: Guest creation round-trip (Req 1.1, 3.1)
- Property 2: Duplicate email rejection (Req 1.2, 4.4)
- Property 3: Duplicate identification rejection (Req 1.3, 4.5)
- Property 5: Partial update field preservation (Req 4.1, 5.3)
- Property 6: List completeness invariant (Req 2.1)
"""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import (
    GuestEmailDuplicateException,
    GuestIdentificationDuplicateException,
)
from app.db.base import Base
from app.models.guest import IdentificationType
from app.repositories.guest_repository import GuestRepository
from app.schemas.guest import GuestCreate, GuestUpdate
from app.services.guest_service import GuestService

# --- Strategies ---

names = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

# Simple, deterministic email/identification via a numeric seed to guarantee
# uniqueness without relying on Hypothesis to avoid collisions.
seeds = st.integers(min_value=1, max_value=10_000)

id_types = st.sampled_from(list(IdentificationType))

phones = st.text(alphabet="0123456789", min_size=7, max_size=20)


def _make_create(seed: int, **overrides) -> GuestCreate:
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": f"guest{seed}@example.com",
        "phone": "5551234",
        "identification_type": IdentificationType.NATIONAL_ID,
        "identification_number": f"ID{seed}",
    }
    data.update(overrides)
    return GuestCreate(**data)


@pytest.fixture
def service_factory():
    """Return a factory that builds a fresh service backed by in-memory SQLite."""

    def _build():
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        return GuestService(GuestRepository(session)), session

    return _build


# --- Property 1: Round-trip ---


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    seed=seeds,
    first_name=names,
    last_name=names,
    phone=phones,
    id_type=id_types,
)
def test_creation_round_trip(
    service_factory, seed, first_name, last_name, phone, id_type
):
    """For valid data, create then get_by_id returns matching fields."""
    service, session = service_factory()
    try:
        data = _make_create(
            seed,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            identification_type=id_type,
        )
        created = service.create_guest(data)
        session.commit()

        fetched = service.get_guest(created.id)
        assert fetched.first_name == data.first_name
        assert fetched.last_name == data.last_name
        assert fetched.email == data.email
        assert fetched.phone == data.phone
        assert fetched.identification_type == data.identification_type
        assert fetched.identification_number == data.identification_number
    finally:
        session.close()


# --- Property 2: Duplicate email rejection ---


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(seed=seeds)
def test_duplicate_email_rejected(service_factory, seed):
    """Second create with same email is rejected; first remains intact."""
    service, session = service_factory()
    try:
        first = service.create_guest(_make_create(seed))
        session.commit()

        # Same email, different identification number.
        dup = _make_create(seed, identification_number=f"OTHER{seed}")
        with pytest.raises(GuestEmailDuplicateException):
            service.create_guest(dup)
        session.rollback()

        assert len(service.list_guests()) == 1
        assert service.get_guest(first.id).email == first.email
    finally:
        session.close()


# --- Property 3: Duplicate identification rejection ---


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(seed=seeds)
def test_duplicate_identification_rejected(service_factory, seed):
    """Second create with same (type, number) is rejected."""
    service, session = service_factory()
    try:
        service.create_guest(_make_create(seed))
        session.commit()

        # Same identification, different email.
        dup = _make_create(seed, email=f"other{seed}@example.com")
        with pytest.raises(GuestIdentificationDuplicateException):
            service.create_guest(dup)
        session.rollback()

        assert len(service.list_guests()) == 1
    finally:
        session.close()


# --- Property 5: Partial update field preservation ---


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(seed=seeds, new_phone=phones)
def test_partial_update_preserves_other_fields(service_factory, seed, new_phone):
    """Updating only phone preserves all other fields, id and created_at."""
    service, session = service_factory()
    try:
        created = service.create_guest(_make_create(seed))
        session.commit()

        original_id = created.id
        original_email = created.email
        original_first = created.first_name
        original_last = created.last_name
        original_created_at = created.created_at
        original_id_number = created.identification_number

        updated = service.update_guest(
            original_id, GuestUpdate(phone=new_phone)
        )
        session.commit()

        assert updated.id == original_id
        assert updated.phone == new_phone
        assert updated.email == original_email
        assert updated.first_name == original_first
        assert updated.last_name == original_last
        assert updated.identification_number == original_id_number
        assert updated.created_at == original_created_at
    finally:
        session.close()


# --- Property 6: List completeness invariant ---


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(n=st.integers(min_value=0, max_value=15))
def test_list_completeness(service_factory, n):
    """For N inserted guests, list_guests returns exactly N."""
    service, session = service_factory()
    try:
        for i in range(1, n + 1):
            service.create_guest(_make_create(i))
        session.commit()

        result = service.list_guests()
        assert len(result) == n
        emails = {g.email for g in result}
        assert len(emails) == n
    finally:
        session.close()
