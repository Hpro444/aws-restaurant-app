"""Tests for RegistrationService automatic role assignment."""

import unittest
import uuid
from unittest.mock import MagicMock, patch

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from commons.exceptions import ApplicationException
    from domain.admin import Admin
    from domain.admin_email import AdminEmail
    from domain.user import Customer, Waiter
    from domain.waiter_emails import WaiterEmail
    from dto.sign_up import SignUpRequest
    from enums.user_role import UserRole
    from services.registration_service import RegistrationService

_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_LOCATION_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")

_REQUEST = SignUpRequest(
    firstName="Jane",
    lastName="Doe",
    email="jane@example.com",
    password="Secure123!",
)

_WAITER_EMAIL_RECORD = WaiterEmail(
    email="jane@example.com",
    location_id=_LOCATION_ID,
)

_ADMIN_EMAIL_RECORD = AdminEmail(email="jane@example.com")


class _ServiceTestCase(unittest.TestCase):
    """Base class: mocked boto3 + fresh RegistrationService with all dependencies mocked."""

    def setUp(self) -> None:
        """Patch boto3 and replace all repository/service collaborators with mocks."""
        patcher = patch("repositories.base_repository.boto3")
        self.mock_boto3 = patcher.start()
        self.mock_boto3.client.return_value = MagicMock()
        self.addCleanup(patcher.stop)

        cognito_patcher = patch("services.cognito_service.boto3")
        self.mock_cognito_boto3 = cognito_patcher.start()
        self.mock_cognito_boto3.client.return_value = MagicMock()
        self.addCleanup(cognito_patcher.stop)

        self.service = RegistrationService()
        self.service._cognito_service = MagicMock()
        self.service._waiter_emails_repo = MagicMock()
        self.service._waiter_repo = MagicMock()
        self.service._customer_repo = MagicMock()
        self.service._admin_emails_repo = MagicMock()
        self.service._admin_repo = MagicMock()

        self.service._cognito_service.register_user.return_value = _USER_ID
        self.service._admin_emails_repo.get.return_value = None


class TestRoleResolution(_ServiceTestCase):
    """Tests that verify the correct role is derived from the waiter-emails list."""

    def test_email_in_admin_list_registers_as_admin(self) -> None:
        """An email present in the admin-emails table must result in UserRole.ADMIN."""
        self.service._admin_emails_repo.get.return_value = _ADMIN_EMAIL_RECORD

        self.service.register_user(_REQUEST)

        self.service._cognito_service.register_user.assert_called_once()
        _, kwargs = self.service._cognito_service.register_user.call_args
        self.assertEqual(kwargs["role"], UserRole.ADMIN)

    def test_email_in_whitelist_registers_as_waiter(self) -> None:
        """An email present in the waiter-emails table must result in UserRole.WAITER."""
        self.service._waiter_emails_repo.get.return_value = _WAITER_EMAIL_RECORD

        self.service.register_user(_REQUEST)

        self.service._cognito_service.register_user.assert_called_once()
        _, kwargs = self.service._cognito_service.register_user.call_args
        self.assertEqual(kwargs["role"], UserRole.WAITER)

    def test_user_email_not_in_waiter_list_registers_as_customer(self) -> None:
        """An email absent from the waiter-emails table must result in UserRole.CUSTOMER."""
        self.service._waiter_emails_repo.get.return_value = None

        self.service.register_user(_REQUEST)

        self.service._cognito_service.register_user.assert_called_once()
        _, kwargs = self.service._cognito_service.register_user.call_args
        self.assertEqual(kwargs["role"], UserRole.CUSTOMER)


class TestDynamoDBPersistence(_ServiceTestCase):
    """Tests that verify the correct repository is used after role resolution."""

    def test_admin_persisted_to_admin_repository(self) -> None:
        """When role resolves to Admin, the record must be written to AdminRepository."""
        self.service._admin_emails_repo.get.return_value = _ADMIN_EMAIL_RECORD

        self.service.register_user(_REQUEST)

        self.service._admin_repo.create.assert_called_once()
        self.service._customer_repo.create.assert_not_called()
        self.service._waiter_repo.create.assert_not_called()

    def test_admin_record_carries_correct_user_fields(self) -> None:
        """The Admin model must reflect the name, email, and sub from the request/Cognito."""
        self.service._admin_emails_repo.get.return_value = _ADMIN_EMAIL_RECORD

        self.service.register_user(_REQUEST)

        admin: Admin = self.service._admin_repo.create.call_args.args[0]
        self.assertEqual(admin.fname, "Jane")
        self.assertEqual(admin.lname, "Doe")
        self.assertEqual(admin.email, "jane@example.com")
        self.assertEqual(str(admin.id), _USER_ID)

    def test_waiter_persisted_to_waiter_repository(self) -> None:
        """When role resolves to Waiter, the record must be written to WaiterRepository."""
        self.service._waiter_emails_repo.get.return_value = _WAITER_EMAIL_RECORD

        self.service.register_user(_REQUEST)

        self.service._waiter_repo.create.assert_called_once()
        self.service._customer_repo.create.assert_not_called()

    def test_customer_persisted_to_customer_repository(self) -> None:
        """When role resolves to Customer, the record must be written to CustomerRepository."""
        self.service._waiter_emails_repo.get.return_value = None

        self.service.register_user(_REQUEST)

        self.service._customer_repo.create.assert_called_once()
        self.service._waiter_repo.create.assert_not_called()

    def test_waiter_record_carries_correct_location_id(self) -> None:
        """The Waiter model passed to the repository must have the location_id from the waiter-emails table."""
        self.service._waiter_emails_repo.get.return_value = _WAITER_EMAIL_RECORD

        self.service.register_user(_REQUEST)

        waiter: Waiter = self.service._waiter_repo.create.call_args.args[0]
        self.assertEqual(waiter.location_id, _LOCATION_ID)

    def test_waiter_record_carries_correct_user_fields(self) -> None:
        """The Waiter model must reflect the name, email, and sub from the request/Cognito."""
        self.service._waiter_emails_repo.get.return_value = _WAITER_EMAIL_RECORD

        self.service.register_user(_REQUEST)

        waiter: Waiter = self.service._waiter_repo.create.call_args.args[0]
        self.assertEqual(waiter.fname, "Jane")
        self.assertEqual(waiter.lname, "Doe")
        self.assertEqual(waiter.email, "jane@example.com")
        self.assertEqual(str(waiter.id), _USER_ID)

    def test_customer_record_carries_correct_user_fields(self) -> None:
        """The Customer model must reflect the name, email, and sub from the request/Cognito."""
        self.service._waiter_emails_repo.get.return_value = None

        self.service.register_user(_REQUEST)

        customer: Customer = self.service._customer_repo.create.call_args.args[0]
        self.assertEqual(customer.fname, "Jane")
        self.assertEqual(customer.lname, "Doe")
        self.assertEqual(customer.email, "jane@example.com")
        self.assertEqual(str(customer.id), _USER_ID)


class TestErrorPropagation(_ServiceTestCase):
    """Tests that verify failures in collaborators surface correctly."""

    def test_cognito_failure_propagates_and_skips_db_write(self) -> None:
        """A Cognito error must propagate without any DynamoDB write."""
        self.service._waiter_emails_repo.get.return_value = None
        self.service._cognito_service.register_user.side_effect = ApplicationException(
            code=409, content="Registration failed"
        )

        with self.assertRaises(ApplicationException):
            self.service.register_user(_REQUEST)

        self.service._customer_repo.create.assert_not_called()
        self.service._waiter_repo.create.assert_not_called()

    def test_waiter_list_check_failure_propagates(self) -> None:
        """A failure reading the waiter-emails table must propagate before Cognito is called."""
        self.service._waiter_emails_repo.get.side_effect = Exception("DynamoDB error")

        with self.assertRaises(Exception):
            self.service.register_user(_REQUEST)

        self.service._cognito_service.register_user.assert_not_called()

    def test_returns_cognito_sub_on_success(self) -> None:
        """register_user must return the Cognito sub UUID string on success."""
        self.service._waiter_emails_repo.get.return_value = None

        result = self.service.register_user(_REQUEST)

        self.assertEqual(result, _USER_ID)
