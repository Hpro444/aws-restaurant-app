import { useEffect, useState } from "react";
import DishCard from "../../../components/common/DishCard";
import type { Dish } from "../../../types/dish";
import { getDishes, type DishSort, type DishType } from "../menu.services";

const baseBtnClass = "font-bold py-1 px-7.5 rounded-lg";
const btnClass = `${baseBtnClass} border border-[var(--color-brand)] text-[var(--color-brand)]`;
const activeBtnClass = `${baseBtnClass} text-white bg-[var(--color-brand)]`;

const sortByOptions: { value: DishSort; label: string }[] = [
  { value: "popularity,desc", label: "Popularity Descending" },
  { value: "popularity,asc", label: "Popularity Ascending" },
  { value: "price,desc", label: "Price: High to Low" },
  { value: "price,asc", label: "Price: Low to High" },
];

const filters: { value: DishType; label: string }[] = [
  { value: "APPETIZER", label: "Appetizers" },
  { value: "MAIN_COURSE", label: "Main Courses" },
  { value: "DESSERT", label: "Desserts" },
  { value: "DRINK", label: "Drinks" },
];

const DEFAULT_FILTER: DishType = "MAIN_COURSE";
const DEFAULT_SORT: DishSort = "popularity,desc";

const DynamicMenu = () => {
  const [selectedFilter, setSelectedFilter] =
    useState<DishType>(DEFAULT_FILTER);
  const [selectedSort, setSelectedSort] = useState<DishSort>(DEFAULT_SORT);
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadDishes = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getDishes({
          dishType: selectedFilter,
          sort: selectedSort,
        });

        if (!cancelled) {
          setDishes(data);
        }
      } catch (err) {
        if (!cancelled) {
          setDishes([]);
          setError(
            err instanceof Error ? err.message : "Failed to load dishes.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadDishes();

    return () => {
      cancelled = true;
    };
  }, [selectedFilter, selectedSort]);

  return (
    <section className="flex flex-col gap-10">
      <div className="flex justify-between">
        <div className="flex gap-4">
          {filters.map((filter) => (
            <button
              key={filter.value}
              className={`cursor-pointer ${filter.value === selectedFilter ? activeBtnClass : btnClass}`}
              onClick={() => setSelectedFilter(filter.value)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>

        <div className="flex gap-4 items-center">
          <p>Sort by:</p>
          <select
            value={selectedSort}
            onChange={(e) => setSelectedSort(e.target.value as DishSort)}
            className="border cursor-pointer font-bold border-[var(--color-brand)] text-[var(--color-brand)] rounded-lg px-2 py-1"
          >
            {sortByOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && (
        <p className="text-[var(--color-text-muted)]">Loading dishes...</p>
      )}
      {error && <p className="text-[var(--color-red-400)]">{error}</p>}

      {!isLoading && !error && dishes.length === 0 && (
        <p className="text-[var(--color-text-muted)]">No dishes found.</p>
      )}

      {!isLoading && !error && dishes.length > 0 && (
        <div className="grid grid-cols-4 gap-8">
          {dishes.map((dish) => (
            <DishCard
              key={dish.id}
              dish={dish}
              imageClassName="mx-auto max-h-[196px] max-w-[196px]"
            />
          ))}
        </div>
      )}
    </section>
  );
};

export default DynamicMenu;
