"""Seed module for customer profiles."""

from domain.user import Customer  # type: ignore[import-not-found]

from seeds.utils import seed_id

_S3 = "https://epam-restaurantapp-dev-eu-west-3-frontend.s3.eu-west-3.amazonaws.com/images"


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 11 demo customers and write them to context['customers']."""
    table = dynamodb.Table(tables["customers"])

    customers = [
        Customer(
            id=seed_id("customer", "alice"),
            fname="Alice",
            lname="Smith",
            email="alice@example.com",
            image_url=f"{_S3}/user_avatar_1.png",
        ),
        Customer(
            id=seed_id("customer", "bob"),
            fname="Bob",
            lname="Johnson",
            email="bob@example.com",
            image_url=f"{_S3}/user_avatar_2.png",
        ),
        Customer(
            id=seed_id("customer", "carol"),
            fname="Carol",
            lname="Williams",
            email="carol@example.com",
            image_url=f"{_S3}/user_avatar_3.png",
        ),
        Customer(
            id=seed_id("customer", "david"),
            fname="David",
            lname="Brown",
            email="david@example.com",
            image_url=f"{_S3}/user_avatar_default.png",
        ),
        Customer(
            id=seed_id("customer", "emma"),
            fname="Emma",
            lname="Davis",
            email="emma@example.com",
            image_url=f"{_S3}/user_avatar_1.png",
        ),
        Customer(
            id=seed_id("customer", "frank"),
            fname="Frank",
            lname="Miller",
            email="frank@example.com",
            image_url=f"{_S3}/user_avatar_2.png",
        ),
        Customer(
            id=seed_id("customer", "grace"),
            fname="Grace",
            lname="Wilson",
            email="grace@example.com",
            image_url=f"{_S3}/user_avatar_3.png",
        ),
        Customer(
            id=seed_id("customer", "henry"),
            fname="Henry",
            lname="Moore",
            email="henry@example.com",
            image_url=f"{_S3}/user_avatar_default.png",
        ),
        Customer(
            id=seed_id("customer", "iris"),
            fname="Iris",
            lname="Taylor",
            email="iris@example.com",
            image_url=f"{_S3}/user_avatar_1.png",
        ),
        Customer(
            id=seed_id("customer", "james"),
            fname="James",
            lname="Anderson",
            email="james@example.com",
            image_url=f"{_S3}/user_avatar_2.png",
        ),
        Customer(
            id=seed_id("customer", "kate"),
            fname="Kate",
            lname="Thompson",
            email="kate@example.com",
            image_url=f"{_S3}/user_avatar_3.png",
        ),
    ]

    with table.batch_writer() as batch:
        for customer in customers:
            batch.put_item(Item=customer.model_dump(mode="json"))

    print(
        f"  ✓ Seeded {len(customers)} customers (Alice, Bob, Carol, David, Emma, Frank, Grace, Henry, Iris, James, Kate)"
    )
    context["customers"] = {c.id: c for c in customers}
