import dish_image from "../../assets/home/dish.png";

const DiscCard = () => {
  return (
    <div className="flex flex-col g-4 p-6 rotate-0 opacity-100 rounded-[24px] gap-4 shadow-[0px_0px_10px_4px_#DADADAB2]">
      <img src={dish_image} alt="Dish" />
      <div className="flex flex-col gap-1">
        <p className="font-medium text-[14px] leading-[24px] align-middle">
          Some text
        </p>
        <p className="flex justify-between font-light text-[12px] leading-[16px] align-middle">
          <span>17$</span>
          <span>430g</span>
        </p>
      </div>
    </div>
  );
};

export default DiscCard;
