"""Seed module for customer profiles."""

from uuid import UUID

from domain.user import Customer  # type: ignore[import-not-found]

_S3 = "https://epam-restaurantapp-dev-eu-west-3-frontend.s3.eu-west-3.amazonaws.com/images"


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 11 demo customers using Cognito subs as DynamoDB IDs.

    Requires ``context["cognito_subs"]`` populated by the cognito_users seeder.
    Writes ``context["customers"]`` keyed by email for downstream seeders.
    """
    table = dynamodb.Table(tables["customers"])
    subs = context["cognito_subs"]

    customers = [
        Customer(
            id=UUID(subs["alice@example.com"]),
            fname="Alice",
            lname="Smith",
            email="alice@example.com",
            image_url=f"{_S3}/user_avatar_1.png",
        ),
        Customer(
            id=UUID(subs["bob@example.com"]),
            fname="Bob",
            lname="Johnson",
            email="bob@example.com",
            image_url=f"{_S3}/user_avatar_2.png",
        ),
        Customer(
            id=UUID(subs["carol@example.com"]),
            fname="Carol",
            lname="Williams",
            email="carol@example.com",
            image_url=f"{_S3}/user_avatar_3.png",
        ),
        Customer(
            id=UUID(subs["david@example.com"]),
            fname="David",
            lname="Brown",
            email="david@example.com",
            image_url=f"{_S3}/user_avatar_default.png",
        ),
        Customer(
            id=UUID(subs["emma@example.com"]),
            fname="Emma",
            lname="Davis",
            email="emma@example.com",
            image_url=f"{_S3}/user_avatar_1.png",
        ),
        Customer(
            id=UUID(subs["frank@example.com"]),
            fname="Frank",
            lname="Miller",
            email="frank@example.com",
            image_url=f"{_S3}/user_avatar_2.png",
        ),
        Customer(
            id=UUID(subs["grace@example.com"]),
            fname="Grace",
            lname="Wilson",
            email="grace@example.com",
            image_url=f"{_S3}/user_avatar_3.png",
        ),
        Customer(
            id=UUID(subs["henry@example.com"]),
            fname="Henry",
            lname="Moore",
            email="henry@example.com",
            image_url=f"{_S3}/user_avatar_default.png",
        ),
        Customer(
            id=UUID(subs["iris@example.com"]),
            fname="Iris",
            lname="Taylor",
            email="iris@example.com",
            image_url=f"{_S3}/user_avatar_1.png",
        ),
        Customer(
            id=UUID(subs["james@example.com"]),
            fname="James",
            lname="Anderson",
            email="james@example.com",
            image_url=f"{_S3}/user_avatar_2.png",
        ),
        Customer(
            id=UUID(subs["kate@example.com"]),
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
    context["customers"] = {c.email: c for c in customers}
