"""Unit tests for reservation Pydantic schemas.

Validates: Requirements 1.3, 3.1, 7.3 (server-managed fields + date validation)
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.reservation import ReservationCreate, ReservationUpdate


def _valid_create(**overrides) -> dict:
    data = {
        "guest_id": 1,
        "room_id": 1,
        "check_in_date": "2026-09-01",
        "check_out_date": "2026-09-05",
    }
    data.update(overrides)
    return data


class TestReservationCreate:
    def test_valid_payload(self):
        model = ReservationCreate(**_valid_create())
        assert model.check_in_date == date(2026, 9, 1)
        assert model.check_out_date == date(2026, 9, 5)

    def test_checkout_before_checkin_rejected(self):
        with pytest.raises(ValidationError):
            ReservationCreate(**_valid_create(check_out_date="2026-08-31"))

    def test_checkout_equal_checkin_rejected(self):
        with pytest.raises(ValidationError):
            ReservationCreate(**_valid_create(check_out_date="2026-09-01"))

    def test_client_total_price_rejected(self):
        """total_price is server-managed: sending it raises 422 (extra=forbid)."""
        with pytest.raises(ValidationError):
            ReservationCreate(**_valid_create(total_price="500.00"))

    def test_client_status_rejected(self):
        with pytest.raises(ValidationError):
            ReservationCreate(**_valid_create(status="confirmed"))

    def test_non_positive_ids_rejected(self):
        with pytest.raises(ValidationError):
            ReservationCreate(**_valid_create(guest_id=0))
        with pytest.raises(ValidationError):
            ReservationCreate(**_valid_create(room_id=-1))


class TestReservationUpdate:
    def test_empty_update_is_valid(self):
        model = ReservationUpdate()
        assert model.model_dump(exclude_unset=True) == {}

    def test_partial_update_single_field(self):
        model = ReservationUpdate(check_out_date="2026-09-10")
        assert model.model_dump(exclude_unset=True) == {
            "check_out_date": date(2026, 9, 10)
        }

    def test_client_total_price_rejected(self):
        with pytest.raises(ValidationError):
            ReservationUpdate(total_price="500.00")

    def test_client_status_rejected(self):
        with pytest.raises(ValidationError):
            ReservationUpdate(status="cancelled")
