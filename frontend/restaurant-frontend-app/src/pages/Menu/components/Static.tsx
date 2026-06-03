import DishCard from "../../../components/common/DishCard";

import dish1 from "../../../assets/menu/strawberry_mint_salad.png";
import dish2 from "../../../assets/menu/pineapple_vanilla_souffle.png";
import dish3 from "../../../assets/menu/avocado_pinenut_bowl.png";
import dish4 from "../../../assets/menu/asparagus_green_salad.png";
import dish5 from "../../../assets/menu/sweetpotato_lentil_salad.png";
import dish6 from "../../../assets/menu/chocolate_berry_mousse.png";
import dish7 from "../../../assets/menu/avocado_egg_toast.png";
import dish8 from "../../../assets/menu/spring_green_salad.png";

const dishes = [
  {
    name: "Fresh Strawberry Mint Salad",
    image_url: dish1,
    price: 15,
    weight_gram: 430,
  },
  {
    name: "Pineapple Tart with Vanilla Soufflé",
    image_url: dish2,
    price: 6,
    weight_gram: 130,
  },
  {
    name: "Avocado Pine Nut Bowl",
    image_url: dish3,
    price: 15,
    weight_gram: 430,
  },
  {
    name: "Asparagus Salad",
    image_url: dish4,
    price: 17,
    weight_gram: 430,
  },
  {
    name: "Roasted Sweet Potato & Lentil Salad",
    image_url: dish5,
    price: 10,
    weight_gram: 430,
  },
  {
    name: "Chocolate Mousse with Berries",
    image_url: dish6,
    price: 9,
    weight_gram: 250,
  },
  {
    name: "Avocado and Egg Toast",
    image_url: dish7,
    price: 9,
    weight_gram: 180,
  },
  {
    name: "Spring Salad",
    image_url: dish8,
    price: 14,
    weight_gram: 430,
  },
];

const StaticMenu = () => {
  return (
    <section className="grid grid-cols-4 grid-rows-2 gap-8">
      {dishes.map((dish, i) => (
        <DishCard key={i} dish={dish} imageClassName="max-w-[196px] max-h-[196px] mx-auto" />
      ))}
    </section>
  );
};

export default StaticMenu;
