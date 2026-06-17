import { useEffect, useState, useCallback } from "react";
import Header from "../../components/header";
import section_image from "../../assets/home/section-image.png";
import DiscCard from "../../components/common/DishCard";
import Layout from "../../components/layout";
import LocationCard from "./components/LocationCard";
import { Link } from "react-router-dom";
import getApiBaseUrl from "../../config/GetApiBaseUrl";
import type { Dish } from "../../types/dish";
import type { Location } from "../../types/location";

const HomePage = () => {
  const [popularDishes, setPopularDishes] = useState<Dish[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [dishesLoading, setDishesLoading] = useState(true);
  const [locationsLoading, setLocationsLoading] = useState(true);
  const [dishesError, setDishesError] = useState<string | null>(null);
  const [locationsError, setLocationsError] = useState<string | null>(null);

  const fetchPopularDishes = useCallback(async () => {
    try {
      setDishesLoading(true);
      setDishesError(null);
      const response = await fetch(`${getApiBaseUrl()}/dishes/popular`);

      if (!response.ok) {
        throw new Error(`Failed to fetch popular dishes: ${response.status}`);
      }

      const data = await response.json();
      setPopularDishes(data);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Failed to fetch popular dishes";
      setDishesError(errorMessage);
      console.error("Error fetching popular dishes:", error);
    } finally {
      setDishesLoading(false);
    }
  }, []);

  const fetchLocations = useCallback(async () => {
    try {
      setLocationsLoading(true);
      setLocationsError(null);
      const response = await fetch(`${getApiBaseUrl()}/locations`);

      if (!response.ok) {
        throw new Error(`Failed to fetch locations: ${response.status}`);
      }

      const data = await response.json();
      setLocations(data);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to fetch locations";
      setLocationsError(errorMessage);
      console.error("Error fetching locations:", error);
    } finally {
      setLocationsLoading(false);
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      await Promise.all([fetchPopularDishes(), fetchLocations()]);
    };

    loadData();
  }, [fetchPopularDishes, fetchLocations]);

  return (
    <>
      <Header />
      <section
        className="relative flex justify-start font-poppins bg-cover bg-center"
        style={{
          backgroundImage: `url(${section_image})`,
        }}
      >
        <div className="max-w-[1440px] w-full mx-auto flex">
          <div className="flex flex-col gap-6 my-10 ml-10 text-white">
            <h1 className="text-[var(--color-brand)] font-poppins font-medium text-[48px] leading-[48px] align-middle">
              Green & Tasty
            </h1>
            <div className="max-w-[339px] flex gap-3 flex-col font-poppins font-light text-[14px] leading-[24px] align-middle">
              <p>
                A network of restaurants in Tbilisi, Georgia, offering fresh,
                locally sourced dishes with a focus on health and
                sustainability.
              </p>
              <p>
                Our diverse menu includes vegetarian and vegan options, crafted
                to highlight the rich flavors of Georgian cuisine with a modern
                twist.
              </p>
            </div>
            <Link
              to="/menu"
              className="pt-3.5 rotate-0 opacity-100 rounded-[8px] bg-[var(--color-brand)] text-white hover:bg-[#009a0b] py-4 text-center"
            >
              View Menu
            </Link>
          </div>
        </div>
      </section>
      <Layout>
        <section className="flex flex-col gap-10">
          <h2 className="font-medium text-[24px] leading-[40px] align-middle">
            Most popular Dishes
          </h2>
          <div className="grid grid-cols-4 gap-8">
            {dishesLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div key={`dish-loading-${index}`} className="animate-pulse">
                  <div className="bg-gray-200 h-48 rounded-lg mb-4"></div>
                  <div className="bg-gray-200 h-4 rounded mb-2"></div>
                  <div className="bg-gray-200 h-4 rounded w-3/4"></div>
                </div>
              ))
            ) : dishesError ? (
              <div className="col-span-4 text-center py-8">
                <p className="text-red-500 mb-4">
                  Error loading popular dishes: {dishesError}
                </p>
              </div>
            ) : popularDishes.length > 0 ? (
              popularDishes
                .slice(0, 4)
                .map((dish) => <DiscCard key={dish.id} dish={dish} />)
            ) : (
              <div className="col-span-4 text-center py-8">
                <p className="text-gray-500">No popular dishes available</p>
              </div>
            )}
          </div>
        </section>
        <section className="flex flex-col gap-10">
          <h2 className="font-medium text-[24px] leading-[40px] align-middle">
            Locations
          </h2>
          <div className="grid grid-cols-3 gap-8">
            {locationsLoading ? (
              Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={`location-loading-${index}`}
                  className="animate-pulse"
                >
                  <div className="bg-gray-200 h-48 rounded-lg mb-4"></div>
                  <div className="bg-gray-200 h-4 rounded mb-2"></div>
                  <div className="bg-gray-200 h-4 rounded w-2/3"></div>
                </div>
              ))
            ) : locationsError ? (
              <div className="col-span-3 text-center py-8">
                <p className="text-red-500 mb-4">
                  Error loading locations: {locationsError}
                </p>
              </div>
            ) : locations.length > 0 ? (
              locations.slice(0, 3).map((location) => (
                <Link to={`/restaurant/${location.id}`} key={location.id}>
                  <LocationCard location={location} />
                </Link>
              ))
            ) : (
              <div className="col-span-3 text-center py-8">
                <p className="text-gray-500">No locations available</p>
              </div>
            )}
          </div>
        </section>
      </Layout>
    </>
  );
};

export default HomePage;
