import dish_image from "../../assets/home/dish.png";
import type { Dish } from "../../types/dish";

const DishCard = ({
  dish,
  imageClassName,
}: {
  dish?: Dish;
  imageClassName?: string;
}) => {
  const dishName = dish?.name || "Some text";
  const dishPrice = dish?.price ? `${dish.price}$` : "17$";
  const dishWeight = dish?.weight_gram ? `${dish.weight_gram}g` : "430g";
  const dishImage = dish?.image_url || dish_image;

  return (
    <div className="flex flex-col p-6 rotate-0 opacity-100 rounded-[24px] gap-4 shadow-[0px_0px_10px_4px_#DADADAB2]">
      <img
        src={dishImage}
        alt={dishName}
        onError={(e) => {
          e.currentTarget.src = dish_image;
        }}
        className={`${imageClassName}`}
      />
      <div className="flex flex-col gap-1">
        <p className="font-medium text-[14px] leading-[24px] align-middle">
          {dishName}
        </p>
        <p className="flex justify-between font-light text-[12px] leading-[16px] align-middle">
          <span>{dishPrice}</span>
          <span>{dishWeight}</span>
        </p>
      </div>
    </div>
  );
};

export default DishCard;
