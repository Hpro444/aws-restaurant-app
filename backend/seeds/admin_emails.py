"""Seed module for the admin-email allow-list."""

from domain.admin_email import AdminEmail  # type: ignore[import-not-found]


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed admin email allow-list so the demo admin account can register."""
    table = dynamodb.Table(tables["admin_emails"])

    entries = [
        AdminEmail(email="admin@example.com"),
    ]

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} admin email entries")
