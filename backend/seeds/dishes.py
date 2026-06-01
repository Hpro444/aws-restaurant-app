"""Seed module for menu dishes."""

from domain.dish import Dish  # type: ignore[import-not-found]
from enums.dish_state import DishState  # type: ignore[import-not-found]
from enums.dish_type import DishType  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item

_S3 = "https://epam-restaurantapp-dev-eu-west-3-frontend.s3.eu-west-3.amazonaws.com/images"

_IMG = {
    "dish1": f"{_S3}/dish1_img.png",
    "chocolate_mousse": f"{_S3}/ChocolateMoussewithBerries.png",
    "pineapple_tart": f"{_S3}/PineappleTartwithVanillaSouffle.png",
    "avocado_bowl": f"{_S3}/avocado_pine_nut_bowl.png",
}


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 4 specialty dishes per location (12 total).

    Every dish is marked specialty=True. Each of the four available food
    images is used exactly once per location.

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
            image_url=_IMG["dish1"],
            specialty=True,
            popular=True,
            price=18.50,
            weight_gram=350,
            state=DishState.AVAILABLE,
            dish_type=DishType.MAIN_COURSE,
        ),
        Dish(
            id=seed_id("dish", "downtown:chocolate-mousse"),
            location_id=locations[downtown_id].id,
            name="Chocolate Mousse with Berries",
            description="Silky dark chocolate mousse layered with fresh mixed berries and a dusting of cocoa powder.",
            image_url=_IMG["chocolate_mousse"],
            specialty=True,
            popular=True,
            price=9.50,
            weight_gram=180,
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "downtown:pineapple-tart"),
            location_id=locations[downtown_id].id,
            name="Pineapple Tart with Vanilla Soufflé",
            description="Caramelised pineapple tart served alongside a light risen vanilla soufflé with crème anglaise.",
            image_url=_IMG["pineapple_tart"],
            specialty=True,
            popular=True,
            price=11.50,
            weight_gram=200,
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "downtown:avocado-bowl"),
            location_id=locations[downtown_id].id,
            name="Avocado Pine Nut Bowl",
            description="Creamy avocado, toasted pine nuts, cherry tomatoes, and mixed greens drizzled with lemon tahini.",
            image_url=_IMG["avocado_bowl"],
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=300,
            state=DishState.AVAILABLE,
            dish_type=DishType.APPETIZER,
        ),
    ]

    airport_dishes = [
        Dish(
            id=seed_id("dish", "airport:chicken-wrap"),
            location_id=locations[airport_id].id,
            name="Grilled Chicken Wrap",
            description="Grilled chicken breast, avocado, mixed greens, and chipotle mayo in a flour tortilla.",
            image_url=_IMG["dish1"],
            specialty=True,
            popular=True,
            price=12.50,
            weight_gram=280,
            state=DishState.AVAILABLE,
            dish_type=DishType.MAIN_COURSE,
        ),
        Dish(
            id=seed_id("dish", "airport:chocolate-mousse"),
            location_id=locations[airport_id].id,
            name="Chocolate Mousse with Berries",
            description="Silky dark chocolate mousse layered with fresh mixed berries and a dusting of cocoa powder.",
            image_url=_IMG["chocolate_mousse"],
            specialty=True,
            popular=True,
            price=9.50,
            weight_gram=180,
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "airport:avocado-bowl"),
            location_id=locations[airport_id].id,
            name="Avocado Pine Nut Bowl",
            description="Creamy avocado, toasted pine nuts, cherry tomatoes, and mixed greens drizzled with lemon tahini.",
            image_url=_IMG["avocado_bowl"],
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=300,
            state=DishState.AVAILABLE,
            dish_type=DishType.APPETIZER,
        ),
        Dish(
            id=seed_id("dish", "airport:pineapple-tart"),
            location_id=locations[airport_id].id,
            name="Pineapple Tart with Vanilla Soufflé",
            description="Caramelised pineapple tart served alongside a light risen vanilla soufflé with crème anglaise.",
            image_url=_IMG["pineapple_tart"],
            specialty=True,
            popular=True,
            price=11.50,
            weight_gram=200,
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
    ]

    old_town_dishes = [
        Dish(
            id=seed_id("dish", "old-town:khachapuri"),
            location_id=locations[old_town_id].id,
            name="Adjarian Khachapuri",
            description="Boat-shaped cheese bread topped with egg yolk and butter.",
            image_url=_IMG["dish1"],
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=420,
            state=DishState.AVAILABLE,
            dish_type=DishType.MAIN_COURSE,
        ),
        Dish(
            id=seed_id("dish", "old-town:pineapple-tart"),
            location_id=locations[old_town_id].id,
            name="Pineapple Tart with Vanilla Soufflé",
            description="Caramelised pineapple tart served alongside a light risen vanilla soufflé with crème anglaise.",
            image_url=_IMG["pineapple_tart"],
            specialty=True,
            popular=True,
            price=11.50,
            weight_gram=200,
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "old-town:avocado-bowl"),
            location_id=locations[old_town_id].id,
            name="Avocado Pine Nut Bowl",
            description="Creamy avocado, toasted pine nuts, cherry tomatoes, and mixed greens drizzled with lemon tahini.",
            image_url=_IMG["avocado_bowl"],
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=300,
            state=DishState.AVAILABLE,
            dish_type=DishType.APPETIZER,
        ),
        Dish(
            id=seed_id("dish", "old-town:chocolate-mousse"),
            location_id=locations[old_town_id].id,
            name="Chocolate Mousse with Berries",
            description="Silky dark chocolate mousse layered with fresh mixed berries and a dusting of cocoa powder.",
            image_url=_IMG["chocolate_mousse"],
            specialty=True,
            popular=True,
            price=9.50,
            weight_gram=180,
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
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
    context["dishes"] = all_dishes
