"""Seed module for the demo admin profile."""

from uuid import UUID

from domain.admin import Admin  # type: ignore[import-not-found]

_S3 = "https://epam-restaurantapp-dev-eu-west-3-frontend.s3.eu-west-3.amazonaws.com/images"


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed the demo admin profile using its Cognito sub as the DynamoDB ID.

    Requires ``context["cognito_subs"]`` populated by the cognito_users seeder
    and the admin email present in the admin-emails allow-list (seeded by the
    admin_emails module). Writes ``context["admins"]`` keyed by email.
    """
    table = dynamodb.Table(tables["admins"])
    subs = context["cognito_subs"]

    admins = [
        Admin(
            id=UUID(subs["admin@example.com"]),
            fname="Ada",
            lname="Admin",
            email="admin@example.com",
            image_url=f"{_S3}/user_avatar_default.png",
        ),
    ]

    with table.batch_writer() as batch:
        for admin in admins:
            batch.put_item(Item=admin.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(admins)} admin profile (admin@example.com)")
    context["admins"] = {a.email: a for a in admins}
