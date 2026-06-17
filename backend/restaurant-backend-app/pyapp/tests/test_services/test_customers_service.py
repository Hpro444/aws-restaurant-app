"""Unit tests for CustomersService."""

from unittest import TestCase
from unittest.mock import MagicMock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.user import Customer
    from dto.customers import CustomerResponse
    from services.customers_service import CustomersService


class TestCustomersService(TestCase):
    """Unit tests that verify customer listing retrieval and DTO mapping."""

    def setUp(self) -> None:
        """Create service with mocked repository and sample domain entities."""
        self.mock_customer_repo = MagicMock()
        self.service = CustomersService(customer_repository=self.mock_customer_repo)
        self.customer_1 = Customer(
            id=uuid4(),
            fname="Jane",
            lname="Doe",
            email="jane@example.com",
            image_url="",
        )
        self.customer_2 = Customer(
            id=uuid4(),
            fname="John",
            lname="Smith",
            email="john@example.com",
            image_url="",
        )

    def test_get_customers_returns_list_of_customer_response(self) -> None:
        """Service should return a DTO list mapped from repository scan output."""
        self.mock_customer_repo.scan.return_value = [self.customer_1, self.customer_2]

        result = self.service.get_customers()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], CustomerResponse)

    def test_get_customers_maps_user_name_as_first_plus_last_name(self) -> None:
        """DTO user_name should be composed as '<first_name> <last_name>'."""
        self.mock_customer_repo.scan.return_value = [self.customer_1]

        result = self.service.get_customers()

        self.assertEqual(result[0].user_name, "Jane Doe")

    def test_get_customers_maps_email_field(self) -> None:
        """DTO email should mirror domain customer email."""
        self.mock_customer_repo.scan.return_value = [self.customer_1]

        result = self.service.get_customers()

        self.assertEqual(result[0].email, "jane@example.com")

    def test_get_customers_returns_empty_list_when_no_customers(self) -> None:
        """Service should return an empty list when repository has no customers."""
        self.mock_customer_repo.scan.return_value = []

        result = self.service.get_customers()

        self.assertEqual(result, [])

    def test_get_customers_calls_repository_scan_once(self) -> None:
        """Service should call repository.scan exactly once."""
        self.mock_customer_repo.scan.return_value = [self.customer_1]

        self.service.get_customers()

        self.mock_customer_repo.scan.assert_called_once()
