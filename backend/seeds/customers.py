"""Seed module for customer profiles."""

from domain.user import Customer  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 3 demo customers and write them to context['customers']."""
    table = dynamodb.Table(tables["customers"])

    customers = [
        Customer(
            id=seed_id("customer", "alice"),
            fname="Alice",
            lname="Smith",
            email="alice@example.com",
            image_url="https://images.example.com/customers/alice.jpg",
        ),
        Customer(
            id=seed_id("customer", "bob"),
            fname="Bob",
            lname="Johnson",
            email="bob@example.com",
            image_url="https://images.example.com/customers/bob.jpg",
        ),
        Customer(
            id=seed_id("customer", "carol"),
            fname="Carol",
            lname="Williams",
            email="carol@example.com",
            image_url="https://images.example.com/customers/carol.jpg",
        ),
    ]

    with table.batch_writer() as batch:
        for customer in customers:
            batch.put_item(Item=customer.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(customers)} customers")
    context["customers"] = {c.id: c for c in customers}
