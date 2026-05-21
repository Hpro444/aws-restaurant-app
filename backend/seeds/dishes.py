"""Seed module for menu dishes."""

from domain.dish import Dish  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item

_S3 = "https://epam-restaurantapp-dev-eu-west-3-frontend.s3.eu-west-3.amazonaws.com/images"


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 6 dishes per location.

    Requires context['locations'] populated by the locations seeder.
    """
    table = dynamodb.Table(tables["dishes"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")
    old_town_id = seed_id("location", "old-town")

    downtown_dishes = [
        Dish(
            id=seed_id("dish", "downtown:carbonara"),
            location_id=locations[downtown_id].id,
            name="Pasta Carbonara",
            description="Creamy Roman pasta with guanciale, egg yolk, and Pecorino Romano.",
            image_url=f"{_S3}/pasta_carbonara.jpg",
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
            image_url=f"{_S3}/margherita_pizza.jpg",
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
            image_url=f"{_S3}/caesar_salad.jpg",
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
            image_url=f"{_S3}/beef_burger.jpg",
            specialty=True,
            popular=True,
            price=16.50,
            weight_gram=450,
        ),
        Dish(
            id=seed_id("dish", "downtown:tomato-soup"),
            location_id=locations[downtown_id].id,
            name="Tomato Soup",
            description="Slow-roasted heirloom tomatoes blended with cream and fresh basil.",
            image_url=f"{_S3}/tomato_soup.jpg",
            specialty=False,
            popular=False,
            price=8.00,
            weight_gram=300,
        ),
        Dish(
            id=seed_id("dish", "downtown:chocolate-mousse"),
            location_id=locations[downtown_id].id,
            name="Chocolate Mousse with Berries",
            description="Silky dark chocolate mousse layered with fresh mixed berries and a dusting of cocoa powder.",
            image_url=f"{_S3}/chocolate_mousse_with_berries.png",
            specialty=True,
            popular=True,
            price=9.50,
            weight_gram=180,
        ),
    ]

    airport_dishes = [
        Dish(
            id=seed_id("dish", "airport:chicken-wrap"),
            location_id=locations[airport_id].id,
            name="Grilled Chicken Wrap",
            description="Grilled chicken breast, avocado, mixed greens, and chipotle mayo in a flour tortilla.",
            image_url=f"{_S3}/grilled_chicken_wrap.jpg",
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
            image_url=f"{_S3}/fish_and_chips.jpg",
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
            image_url=f"{_S3}/greek_salad.jpg",
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
            image_url=f"{_S3}/club_sandwich.jpg",
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
            image_url=f"{_S3}/minestrone_soup.jpg",
            specialty=False,
            popular=False,
            price=7.50,
            weight_gram=300,
        ),
        Dish(
            id=seed_id("dish", "airport:sweet-potato-salad"),
            location_id=locations[airport_id].id,
            name="Roasted Sweet Potato Lentil Salad",
            description="Warm roasted sweet potato wedges over spiced green lentils, pomegranate, and tahini dressing.",
            image_url=f"{_S3}/roasted_sweet_potato_lentil_salad.jpg",
            specialty=True,
            popular=True,
            price=12.00,
            weight_gram=320,
        ),
    ]

    old_town_dishes = [
        Dish(
            id=seed_id("dish", "old-town:khachapuri"),
            location_id=locations[old_town_id].id,
            name="Adjarian Khachapuri",
            description="Boat-shaped cheese bread topped with egg yolk and butter.",
            image_url=f"{_S3}/adjarian_khachapuri.jpg",
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=420,
        ),
        Dish(
            id=seed_id("dish", "old-town:khinkali"),
            location_id=locations[old_town_id].id,
            name="Khinkali",
            description="Traditional Georgian dumplings filled with spiced beef and broth.",
            image_url=f"{_S3}/khinkali.jpg",
            specialty=True,
            popular=True,
            price=12.00,
            weight_gram=360,
        ),
        Dish(
            id=seed_id("dish", "old-town:mtsvadi"),
            location_id=locations[old_town_id].id,
            name="Mtsvadi",
            description="Charcoal-grilled pork skewers served with pickled onions and tkemali.",
            image_url=f"{_S3}/mtsvadi.jpg",
            specialty=True,
            popular=True,
            price=17.00,
            weight_gram=380,
        ),
        Dish(
            id=seed_id("dish", "old-town:lobio"),
            location_id=locations[old_town_id].id,
            name="Lobio",
            description="Slow-cooked red bean stew with herbs and cornbread.",
            image_url=f"{_S3}/lobio.jpg",
            specialty=False,
            popular=False,
            price=9.50,
            weight_gram=300,
        ),
        Dish(
            id=seed_id("dish", "old-town:churchkhela"),
            location_id=locations[old_town_id].id,
            name="Churchkhela",
            description="Walnuts threaded and dipped in thickened grape must.",
            image_url=f"{_S3}/churchkhela.jpg",
            specialty=False,
            popular=False,
            price=6.00,
            weight_gram=120,
        ),
        Dish(
            id=seed_id("dish", "old-town:pineapple-tart"),
            location_id=locations[old_town_id].id,
            name="Pineapple Tart with Vanilla Soufflé",
            description="Caramelised pineapple tart served alongside a light risen vanilla soufflé with crème anglaise.",
            image_url=f"{_S3}/pineapple_tartwith_vanilla_souffle.png",
            specialty=True,
            popular=True,
            price=11.50,
            weight_gram=200,
        ),
    ]

    all_dishes = downtown_dishes + airport_dishes + old_town_dishes

    with table.batch_writer() as batch:
        for dish in all_dishes:
            item = to_item(dish)

            # DynamoDB GSI key types do not support BOOL.
            # Persist `popular` as numeric 1/0 because the GSI key uses
            # the same attribute name and key attributes cannot be BOOL.
            item["popular"] = 1 if dish.popular else 0

            batch.put_item(Item=item)

    print(
        "  ✓ Seeded "
        f"{len(all_dishes)} dishes "
        f"({len(downtown_dishes)} Downtown, "
        f"{len(airport_dishes)} Airport, "
        f"{len(old_town_dishes)} Old Town)"
    )
