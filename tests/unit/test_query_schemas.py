"""Unit tests for query-param validation (422 semantics)."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.query import AvailabilityQuery, HistoryQuery


class TestAvailabilityQuery:
    def test_valid(self):
        q = AvailabilityQuery(
            check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 5)
        )
        assert q.check_out_date > q.check_in_date

    def test_checkout_before_checkin_rejected(self):
        with pytest.raises(ValidationError):
            AvailabilityQuery(
                check_in_date=date(2026, 9, 5), check_out_date=date(2026, 9, 1)
            )

    def test_checkout_equal_checkin_rejected(self):
        with pytest.raises(ValidationError):
            AvailabilityQuery(
                check_in_date=date(2026, 9, 1), check_out_date=date(2026, 9, 1)
            )


class TestHistoryQueryDatesBothOrNeither:
    def test_both_omitted_valid(self):
        q = HistoryQuery()
        assert q.date_from is None and q.date_to is None

    def test_both_provided_valid(self):
        q = HistoryQuery(date_from=date(2026, 9, 1), date_to=date(2026, 9, 5))
        assert q.date_from < q.date_to

    def test_only_date_from_rejected(self):
        with pytest.raises(ValidationError):
            HistoryQuery(date_from=date(2026, 9, 1))

    def test_only_date_to_rejected(self):
        with pytest.raises(ValidationError):
            HistoryQuery(date_to=date(2026, 9, 5))

    def test_both_provided_bad_order_rejected(self):
        with pytest.raises(ValidationError):
            HistoryQuery(date_from=date(2026, 9, 5), date_to=date(2026, 9, 1))

    def test_both_provided_equal_rejected(self):
        with pytest.raises(ValidationError):
            HistoryQuery(date_from=date(2026, 9, 1), date_to=date(2026, 9, 1))


class TestHistoryQueryOtherFilters:
    def test_status_within_enum_valid(self):
        q = HistoryQuery(status="cancelled")
        assert q.status is not None

    def test_status_outside_enum_rejected(self):
        with pytest.raises(ValidationError):
            HistoryQuery(status="not_a_status")

    def test_non_positive_ids_rejected(self):
        with pytest.raises(ValidationError):
            HistoryQuery(guest_id=0)
        with pytest.raises(ValidationError):
            HistoryQuery(room_id=-1)
