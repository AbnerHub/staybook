"""Unit tests for StayService using mocked repositories.

Validates: Requirements 2.3 (not found), 4.3 (not found), 3.4 (today provider),
5.3 (reuse RoomRepository).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    ReservationNotFoundException,
    RoomNotFoundException,
)
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType
from app.services.stay_service import StayService

CHECK_IN = date(2026, 9, 1)
CHECK_OUT = date(2026, 9, 5)


def _reservation(status=ReservationStatus.CONFIRMED):
    return Reservation(
        id=1, guest_id=1, room_id=1,
        check_in_date=CHECK_IN, check_out_date=CHECK_OUT,
        status=status, total_price=Decimal("400.00"),
    )


def _room():
    return Room(
        id=1, room_number="101", room_type=RoomType.INDIVIDUAL,
        price_per_night=Decimal("100.00"), capacity=2,
        status=RoomStatus.DISPONIBLE,
    )


def _service(reservation_repo, room_repo, today=CHECK_IN):
    return StayService(
        session=MagicMock(),
        reservation_repository=reservation_repo,
        room_repository=room_repo,
        today_provider=lambda: today,
    )


class TestCheckInNotFound:
    def test_reservation_not_found(self):
        res_repo = MagicMock()
        res_repo.get_by_id.return_value = None
        room_repo = MagicMock()
        service = _service(res_repo, room_repo)
        with pytest.raises(ReservationNotFoundException):
            service.check_in(999)

    def test_room_not_found(self):
        res_repo = MagicMock()
        res_repo.get_by_id.return_value = _reservation()
        room_repo = MagicMock()
        room_repo.get_by_id.return_value = None
        service = _service(res_repo, room_repo)
        with pytest.raises(RoomNotFoundException):
            service.check_in(1)


class TestCheckOutNotFound:
    def test_reservation_not_found(self):
        res_repo = MagicMock()
        res_repo.get_by_id.return_value = None
        room_repo = MagicMock()
        service = _service(res_repo, room_repo)
        with pytest.raises(ReservationNotFoundException):
            service.check_out(999)


class TestSuccessfulFlowCommits:
    def test_check_in_commits_once(self):
        res_repo = MagicMock()
        res_repo.get_by_id.return_value = _reservation()
        room_repo = MagicMock()
        room_repo.get_by_id.return_value = _room()
        session = MagicMock()
        service = StayService(
            session=session,
            reservation_repository=res_repo,
            room_repository=room_repo,
            today_provider=lambda: CHECK_IN,
        )
        result = service.check_in(1)
        assert result.status == ReservationStatus.CHECKED_IN
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

    def test_check_out_commits_once(self):
        res_repo = MagicMock()
        res_repo.get_by_id.return_value = _reservation(ReservationStatus.CHECKED_IN)
        room_repo = MagicMock()
        room_repo.get_by_id.return_value = _room()
        session = MagicMock()
        service = StayService(
            session=session,
            reservation_repository=res_repo,
            room_repository=room_repo,
            today_provider=lambda: CHECK_OUT,
        )
        result = service.check_out(1)
        assert result.status == ReservationStatus.CHECKED_OUT
        session.commit.assert_called_once()
