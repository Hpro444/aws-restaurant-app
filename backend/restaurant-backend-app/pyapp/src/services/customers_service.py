"""Service for listing customers."""

from dto.customers import CustomerResponse
from repositories.customer_repository import CustomerRepository


class CustomersService:
    """Handles retrieval and response mapping for customer listings."""

    def __init__(
        self,
        customer_repository: CustomerRepository | None = None,
    ) -> None:
        """Initialize dependencies, creating them if not provided."""
        self._customer_repository = customer_repository or CustomerRepository()

    def get_customers(self) -> list[CustomerResponse]:
        """Return all customers mapped to the public customers response contract."""
        customers = self._customer_repository.scan()

        return [
            CustomerResponse(
                id=customer.id,
                user_name=f"{customer.fname} {customer.lname}",
                email=customer.email,
            )
            for customer in customers
        ]
