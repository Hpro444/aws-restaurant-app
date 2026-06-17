"""Seed module for restaurant tables."""

from domain.table import Table  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 6 tables per location and write them to context['tables'].

    Requires context['locations'] populated by the locations seeder.
    """
    table = dynamodb.Table(tables["tables"])
    locations = context["locations"]

    tables_list = []
    for location_id, location_obj in locations.items():
        for table_num in range(1, 7):
            t = Table(
                id=seed_id("table", f"{location_id}:{table_num}"),
                table_number=table_num,
                capacity=10 if table_num % 2 == 0 else 5,
                location_id=location_obj.id,
            )
            tables_list.append(t)

    with table.batch_writer() as batch:
        for t in tables_list:
            batch.put_item(Item=t.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(tables_list)} tables")
    context["tables"] = tables_list
