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

_NUTRITION = {
    "carbonara": {
        "calories": "510 kcal",
        "carbohydrates": "52 g",
        "fats": "22 g",
        "proteins": "24 g",
        "vitamins": "B2, B12",
    },
    "chocolate_mousse": {
        "calories": "340 kcal",
        "carbohydrates": "31 g",
        "fats": "21 g",
        "proteins": "5 g",
        "vitamins": "E, K",
    },
    "pineapple_tart": {
        "calories": "360 kcal",
        "carbohydrates": "44 g",
        "fats": "18 g",
        "proteins": "6 g",
        "vitamins": "C, B6",
    },
    "avocado_bowl": {
        "calories": "290 kcal",
        "carbohydrates": "19 g",
        "fats": "20 g",
        "proteins": "8 g",
        "vitamins": "A, C, E",
    },
    "chicken_wrap": {
        "calories": "430 kcal",
        "carbohydrates": "38 g",
        "fats": "18 g",
        "proteins": "29 g",
        "vitamins": "B3, B6",
    },
    "khachapuri": {
        "calories": "620 kcal",
        "carbohydrates": "56 g",
        "fats": "31 g",
        "proteins": "25 g",
        "vitamins": "A, D",
    },
    "shrimp_bruschetta": {
        "calories": "260 kcal",
        "carbohydrates": "21 g",
        "fats": "11 g",
        "proteins": "17 g",
        "vitamins": "B12, C",
    },
    "berry_spritz": {
        "calories": "140 kcal",
        "carbohydrates": "18 g",
        "fats": "0 g",
        "proteins": "0 g",
        "vitamins": "C",
    },
    "club_sandwich": {
        "calories": "470 kcal",
        "carbohydrates": "35 g",
        "fats": "24 g",
        "proteins": "27 g",
        "vitamins": "B3, B6",
    },
    "citrus_iced_tea": {
        "calories": "95 kcal",
        "carbohydrates": "22 g",
        "fats": "0 g",
        "proteins": "0 g",
        "vitamins": "C",
    },
    "mushroom_soup": {
        "calories": "210 kcal",
        "carbohydrates": "16 g",
        "fats": "12 g",
        "proteins": "8 g",
        "vitamins": "D, B2",
    },
    "mulled_wine": {
        "calories": "180 kcal",
        "carbohydrates": "20 g",
        "fats": "0 g",
        "proteins": "0 g",
        "vitamins": "C",
    },
}


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 6 specialty dishes per location (18 total).

    Every dish is marked specialty=True. Each of the four available food
    images may be reused across dishes and locations.

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
            description="Creamy Roman pasta with guanciale, egg yolk, and Pecorino Romano. Dietary: gluten free.",
            image_url=_IMG["dish1"],
            specialty=True,
            popular=True,
            price=18.50,
            weight_gram=350,
            **_NUTRITION["carbonara"],
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
            **_NUTRITION["chocolate_mousse"],
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "downtown:pineapple-tart"),
            location_id=locations[downtown_id].id,
            name="Pineapple Tart with Vanilla Soufflé",
            description="Caramelised pineapple tart served alongside a light risen vanilla soufflé with crème anglaise. Dietary: vegetarian.",
            image_url=_IMG["pineapple_tart"],
            specialty=True,
            popular=True,
            price=11.50,
            weight_gram=200,
            **_NUTRITION["pineapple_tart"],
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "downtown:avocado-bowl"),
            location_id=locations[downtown_id].id,
            name="Avocado Pine Nut Bowl",
            description="Creamy avocado, toasted pine nuts, cherry tomatoes, and mixed greens drizzled with lemon tahini. Dietary: vegan, vegetarian, dairy free.",
            image_url=_IMG["avocado_bowl"],
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=300,
            **_NUTRITION["avocado_bowl"],
            state=DishState.AVAILABLE,
            dish_type=DishType.APPETIZER,
        ),
        Dish(
            id=seed_id("dish", "downtown:shrimp-bruschetta"),
            location_id=locations[downtown_id].id,
            name="Shrimp Bruschetta",
            description="Toasted sourdough topped with garlic butter shrimp, cherry tomatoes, and lemon herb ricotta.",
            image_url=_IMG["dish1"],
            specialty=True,
            popular=False,
            price=10.90,
            weight_gram=190,
            **_NUTRITION["shrimp_bruschetta"],
            state=DishState.ON_STOP,
            dish_type=DishType.APPETIZER,
        ),
        Dish(
            id=seed_id("dish", "downtown:berry-spritz"),
            location_id=locations[downtown_id].id,
            name="Berry Spritz",
            description="Sparkling berry drink with raspberry puree, citrus syrup, and fresh mint served over ice.",
            image_url=_IMG["chocolate_mousse"],
            specialty=True,
            popular=False,
            price=6.50,
            weight_gram=300,
            **_NUTRITION["berry_spritz"],
            state=DishState.AVAILABLE,
            dish_type=DishType.DRINK,
        ),
    ]

    airport_dishes = [
        Dish(
            id=seed_id("dish", "airport:chicken-wrap"),
            location_id=locations[airport_id].id,
            name="Grilled Chicken Wrap",
            description="Grilled chicken breast, avocado, mixed greens, and chipotle mayo in a flour tortilla. Dietary: dairy free.",
            image_url=_IMG["dish1"],
            specialty=True,
            popular=True,
            price=12.50,
            weight_gram=280,
            **_NUTRITION["chicken_wrap"],
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
            **_NUTRITION["chocolate_mousse"],
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "airport:avocado-bowl"),
            location_id=locations[airport_id].id,
            name="Avocado Pine Nut Bowl",
            description="Creamy avocado, toasted pine nuts, cherry tomatoes, and mixed greens drizzled with lemon tahini. Dietary: vegan, vegetarian, gluten free, dairy free.",
            image_url=_IMG["avocado_bowl"],
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=300,
            **_NUTRITION["avocado_bowl"],
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
            **_NUTRITION["pineapple_tart"],
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "airport:club-sandwich"),
            location_id=locations[airport_id].id,
            name="Airport Club Sandwich",
            description="Triple-layer sandwich with roasted turkey, crispy bacon, tomato, lettuce, and mustard aioli.",
            image_url=_IMG["dish1"],
            specialty=True,
            popular=True,
            price=14.20,
            weight_gram=340,
            **_NUTRITION["club_sandwich"],
            state=DishState.ON_STOP,
            dish_type=DishType.MAIN_COURSE,
        ),
        Dish(
            id=seed_id("dish", "airport:citrus-iced-tea"),
            location_id=locations[airport_id].id,
            name="Citrus Iced Tea",
            description="Chilled black tea infused with orange, lemon, and a touch of blossom honey.",
            image_url=_IMG["pineapple_tart"],
            specialty=True,
            popular=False,
            price=5.20,
            weight_gram=320,
            **_NUTRITION["citrus_iced_tea"],
            state=DishState.AVAILABLE,
            dish_type=DishType.DRINK,
        ),
    ]

    old_town_dishes = [
        Dish(
            id=seed_id("dish", "old-town:khachapuri"),
            location_id=locations[old_town_id].id,
            name="Adjarian Khachapuri",
            description="Boat-shaped cheese bread topped with egg yolk and butter. Dietary: vegetarian.",
            image_url=_IMG["dish1"],
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=420,
            **_NUTRITION["khachapuri"],
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
            **_NUTRITION["pineapple_tart"],
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "old-town:avocado-bowl"),
            location_id=locations[old_town_id].id,
            name="Avocado Pine Nut Bowl",
            description="Creamy avocado, toasted pine nuts, cherry tomatoes, and mixed greens drizzled with lemon tahini. Dietary: vegan, vegetarian, gluten free, dairy free.",
            image_url=_IMG["avocado_bowl"],
            specialty=True,
            popular=True,
            price=13.50,
            weight_gram=300,
            **_NUTRITION["avocado_bowl"],
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
            **_NUTRITION["chocolate_mousse"],
            state=DishState.AVAILABLE,
            dish_type=DishType.DESSERT,
        ),
        Dish(
            id=seed_id("dish", "old-town:mushroom-soup"),
            location_id=locations[old_town_id].id,
            name="Forest Mushroom Soup",
            description="Velvety soup of roasted mushrooms, thyme, and cream finished with truffle oil and croutons.",
            image_url=_IMG["avocado_bowl"],
            specialty=True,
            popular=False,
            price=8.80,
            weight_gram=260,
            **_NUTRITION["mushroom_soup"],
            state=DishState.AVAILABLE,
            dish_type=DishType.APPETIZER,
        ),
        Dish(
            id=seed_id("dish", "old-town:mulled-wine"),
            location_id=locations[old_town_id].id,
            name="Spiced Mulled Wine",
            description="Warm red wine infused with orange peel, clove, cinnamon, and star anise for a rich aromatic finish.",
            image_url=_IMG["chocolate_mousse"],
            specialty=True,
            popular=True,
            price=7.40,
            weight_gram=250,
            **_NUTRITION["mulled_wine"],
            state=DishState.ON_STOP,
            dish_type=DishType.DRINK,
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
