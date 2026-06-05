import DiscCard from "../../../components/common/DishCard";

const baseBtnClass = "font-bold py-1 px-7.5 rounded-lg";
const btnClass = `${baseBtnClass} border border-[var(--color-brand)] text-[var(--color-brand)]`;
const activeBtnClass = `${baseBtnClass} text-white bg-[var(--color-brand)]`;

const sortByOptions = [
  { value: "popularity-desc", label: "Popularity Descending" },
  { value: "price-desc", label: "Price: High to Low" },
  { value: "popularity", label: "Popularity" },
];

const filters = [
  { value: "appetizers", label: "Appetizers" },
  { value: "main-courses", label: "Main Courses" },
  { value: "desserts", label: "Desserts" },
];

const DynamicMenu = () => {
  return (
    <section className="flex flex-col gap-10">
      <div className="flex justify-between">
        <div className="flex gap-4">
          {filters.map((filter) => (
            <button
              key={filter.value}
              className={
                filter.value === "main-courses" ? activeBtnClass : btnClass
              }
            >
              {filter.label}
            </button>
          ))}
        </div>
        <div className="flex gap-4 items-center">
          <p>Sort by:</p>
          <select className="border font-bold border-[var(--color-brand)] text-[var(--color-brand)] rounded-lg px-2 py-1">
            {sortByOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-8">
        {Array.from({ length: 4 }).map((_, index) => (
          <DiscCard
            key={index}
            imageClassName="mx-auto max-h-[196px] max-w-[196px]"
          />
        ))}
      </div>
    </section>
  );
};

export default DynamicMenu;
