"""Seed module for menu dishes."""

from domain.dish import Dish  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 5 dishes per location.

    Requires context['locations'] populated by the locations seeder.
    """
    table = dynamodb.Table(tables["dishes"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")

    downtown_dishes = [
        Dish(
            id=seed_id("dish", "downtown:carbonara"),
            location_id=locations[downtown_id].id,
            name="Pasta Carbonara",
            description="Creamy Roman pasta with guanciale, egg yolk, and Pecorino Romano.",
            image_url="https://images.example.com/dishes/carbonara.jpg",
            specialty=True,
            popular=True,
            price=18.50,
            weight_gram=350,
        ),
        Dish(
            id=seed_id("dish", "downtown:margherita"),
            location_id=locations[downtown_id].id,
            name="Margherita Pizza",
            description="Classic Neapolitan pizza with San Marzano tomato, fresh mozzarella, and basil.",
            image_url="https://images.example.com/dishes/margherita.jpg",
            specialty=True,
            popular=True,
            price=14.00,
            weight_gram=400,
        ),
        Dish(
            id=seed_id("dish", "downtown:caesar"),
            location_id=locations[downtown_id].id,
            name="Caesar Salad",
            description="Crisp romaine lettuce, house-made Caesar dressing, croutons, and Parmesan.",
            image_url="https://images.example.com/dishes/caesar.jpg",
            specialty=False,
            popular=False,
            price=11.00,
            weight_gram=250,
        ),
        Dish(
            id=seed_id("dish", "downtown:burger"),
            location_id=locations[downtown_id].id,
            name="Beef Burger",
            description="180 g prime beef patty, aged cheddar, caramelised onions, and brioche bun.",
            image_url="https://images.example.com/dishes/burger.jpg",
            specialty=False,
            popular=True,
            price=16.50,
            weight_gram=450,
        ),
        Dish(
            id=seed_id("dish", "downtown:tomato-soup"),
            location_id=locations[downtown_id].id,
            name="Tomato Soup",
            description="Slow-roasted heirloom tomatoes blended with cream and fresh basil.",
            image_url="https://images.example.com/dishes/tomato-soup.jpg",
            specialty=False,
            popular=False,
            price=8.00,
            weight_gram=300,
        ),
    ]

    airport_dishes = [
        Dish(
            id=seed_id("dish", "airport:chicken-wrap"),
            location_id=locations[airport_id].id,
            name="Grilled Chicken Wrap",
            description="Grilled chicken breast, avocado, mixed greens, and chipotle mayo in a flour tortilla.",
            image_url="https://images.example.com/dishes/chicken-wrap.jpg",
            specialty=True,
            popular=True,
            price=12.50,
            weight_gram=280,
        ),
        Dish(
            id=seed_id("dish", "airport:fish-chips"),
            location_id=locations[airport_id].id,
            name="Fish & Chips",
            description="Beer-battered cod fillet with thick-cut chips, mushy peas, and tartare sauce.",
            image_url="https://images.example.com/dishes/fish-chips.jpg",
            specialty=True,
            popular=True,
            price=15.00,
            weight_gram=500,
        ),
        Dish(
            id=seed_id("dish", "airport:greek-salad"),
            location_id=locations[airport_id].id,
            name="Greek Salad",
            description="Tomato, cucumber, red onion, Kalamata olives, and feta with oregano vinaigrette.",
            image_url="https://images.example.com/dishes/greek-salad.jpg",
            specialty=False,
            popular=False,
            price=10.00,
            weight_gram=220,
        ),
        Dish(
            id=seed_id("dish", "airport:club-sandwich"),
            location_id=locations[airport_id].id,
            name="Club Sandwich",
            description="Triple-decker with smoked turkey, bacon, lettuce, tomato, and honey mustard.",
            image_url="https://images.example.com/dishes/club-sandwich.jpg",
            specialty=False,
            popular=False,
            price=11.50,
            weight_gram=320,
        ),
        Dish(
            id=seed_id("dish", "airport:minestrone"),
            location_id=locations[airport_id].id,
            name="Minestrone Soup",
            description="Hearty Italian vegetable soup with cannellini beans, pasta, and Parmesan.",
            image_url="https://images.example.com/dishes/minestrone.jpg",
            specialty=False,
            popular=False,
            price=7.50,
            weight_gram=300,
        ),
    ]

    all_dishes = downtown_dishes + airport_dishes

    with table.batch_writer() as batch:
        for dish in all_dishes:
            item = to_item(dish)

            # DynamoDB GSI key types do not support BOOL.
            # Persist `popular` as numeric 1/0 because the GSI key uses
            # the same attribute name and key attributes cannot be BOOL.
            item["popular"] = 1 if dish.popular else 0

            batch.put_item(Item=item)

    print(
        f"  ✓ Seeded {len(all_dishes)} dishes ({len(downtown_dishes)} Downtown, {len(airport_dishes)} Airport)"
    )
