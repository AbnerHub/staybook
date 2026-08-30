"""Unit tests for the GuestService business logic layer.

Validates Requirements: 1.1, 1.2, 1.3, 2.1, 3.2, 4.1, 4.2, 4.4, 4.5, 5.3, 9.1
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    GuestEmailDuplicateException,
    GuestIdentificationDuplicateException,
    GuestNotFoundException,
)
from app.models.guest import Guest, IdentificationType
from app.schemas.guest import GuestCreate, GuestUpdate
from app.services.guest_service import GuestService


@pytest.fixture
def mock_repository():
    return MagicMock()


@pytest.fixture
def service(mock_repository):
    return GuestService(repository=mock_repository)


@pytest.fixture
def sample_guest():
    return Guest(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="5551234",
        identification_type=IdentificationType.NATIONAL_ID,
        identification_number="X1234567",
    )


def _create_data(**overrides) -> GuestCreate:
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "5551234",
        "identification_type": IdentificationType.NATIONAL_ID,
        "identification_number": "X1234567",
    }
    data.update(overrides)
    return GuestCreate(**data)


class TestCreateGuest:
    def test_create_success(self, service, mock_repository, sample_guest):
        mock_repository.get_by_email.return_value = None
        mock_repository.get_by_identification.return_value = None
        mock_repository.create.return_value = sample_guest

        result = service.create_guest(_create_data())

        assert result is sample_guest
        mock_repository.create.assert_called_once()

    def test_create_duplicate_email_raises(self, service, mock_repository, sample_guest):
        mock_repository.get_by_email.return_value = sample_guest

        with pytest.raises(GuestEmailDuplicateException):
            service.create_guest(_create_data())
        mock_repository.create.assert_not_called()

    def test_create_duplicate_identification_raises(
        self, service, mock_repository, sample_guest
    ):
        mock_repository.get_by_email.return_value = None
        mock_repository.get_by_identification.return_value = sample_guest

        with pytest.raises(GuestIdentificationDuplicateException):
            service.create_guest(_create_data())
        mock_repository.create.assert_not_called()

    @patch("app.services.guest_service.audit_log")
    def test_create_calls_audit_log(
        self, mock_audit, service, mock_repository, sample_guest
    ):
        mock_repository.get_by_email.return_value = None
        mock_repository.get_by_identification.return_value = None
        mock_repository.create.return_value = sample_guest

        service.create_guest(_create_data())

        mock_audit.assert_called_once_with("create", sample_guest.id, "success")


class TestGetGuest:
    def test_returns_guest(self, service, mock_repository, sample_guest):
        mock_repository.get_by_id.return_value = sample_guest
        assert service.get_guest(1) is sample_guest

    def test_not_found_raises(self, service, mock_repository):
        mock_repository.get_by_id.return_value = None
        with pytest.raises(GuestNotFoundException):
            service.get_guest(999)


class TestListGuests:
    def test_delegates_to_repository(self, service, mock_repository, sample_guest):
        mock_repository.get_all.return_value = [sample_guest]
        assert service.list_guests() == [sample_guest]


class TestUpdateGuest:
    def test_not_found_raises(self, service, mock_repository):
        mock_repository.get_by_id.return_value = None
        with pytest.raises(GuestNotFoundException):
            service.update_guest(999, GuestUpdate(phone="5559999"))

    def test_partial_update_applies_only_given_fields(
        self, service, mock_repository, sample_guest
    ):
        mock_repository.get_by_id.return_value = sample_guest
        mock_repository.update.side_effect = lambda g: g

        result = service.update_guest(1, GuestUpdate(phone="5559999"))

        assert result.phone == "5559999"
        assert result.email == "john.doe@example.com"
        assert result.first_name == "John"

    def test_update_email_to_existing_raises(
        self, service, mock_repository, sample_guest
    ):
        mock_repository.get_by_id.return_value = sample_guest
        other = Guest(id=2, email="taken@example.com")
        mock_repository.get_by_email.return_value = other

        with pytest.raises(GuestEmailDuplicateException):
            service.update_guest(1, GuestUpdate(email="taken@example.com"))
        mock_repository.update.assert_not_called()

    def test_update_same_email_does_not_raise(
        self, service, mock_repository, sample_guest
    ):
        mock_repository.get_by_id.return_value = sample_guest
        mock_repository.update.side_effect = lambda g: g

        result = service.update_guest(
            1, GuestUpdate(email="john.doe@example.com", phone="5550000")
        )
        assert result.phone == "5550000"
        mock_repository.get_by_email.assert_not_called()

    def test_update_identification_to_existing_raises(
        self, service, mock_repository, sample_guest
    ):
        mock_repository.get_by_id.return_value = sample_guest
        other = Guest(
            id=2,
            identification_type=IdentificationType.PASSPORT,
            identification_number="P999",
        )
        mock_repository.get_by_identification.return_value = other

        with pytest.raises(GuestIdentificationDuplicateException):
            service.update_guest(
                1,
                GuestUpdate(
                    identification_type=IdentificationType.PASSPORT,
                    identification_number="P999",
                ),
            )
        mock_repository.update.assert_not_called()

    @patch("app.services.guest_service.audit_log")
    def test_update_calls_audit_log(
        self, mock_audit, service, mock_repository, sample_guest
    ):
        mock_repository.get_by_id.return_value = sample_guest
        mock_repository.update.side_effect = lambda g: g

        service.update_guest(1, GuestUpdate(phone="5559999"))

        mock_audit.assert_called_once_with("update", sample_guest.id, "success")
