import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Header from "../../components/header";
import locationImg from "../../assets/restaurant/location.png";
import DiscCard from "../../components/common/DishCard";
import FeedbackCard, {
  type Feedback,
} from "../../components/common/FeedbackCard";
import star_icon from "../../assets/restaurant/star-icon.png";
import location_icon from "../../assets/restaurant/location-icon.png";
import arrow_right_icon from "../../assets/restaurant/arrow-right-icon.png";
import getApiBaseUrl from "../../config/GetApiBaseUrl";

type LocationData = {
  id: string;
  name: string;
  address: string;
  description: string;
  rating?: number;
  image?: string;
};

type Dish = {
  id: string;
  name: string;
  description?: string;
  price: number;
  image?: string;
  weight?: string | number;
};

type FeedbackResponse = {
  totalPages: number;
  totalElements: number;
  size: number;
  content: Feedback[];
  number: number;
  sort: string[];
  first: boolean;
  last: boolean;
  numberOfElements: number;
  pageable: {
    offset: number;
    sort: string[];
    paged: boolean;
    pageSize: number;
    pageNumber: number;
    unpaged: boolean;
  };
  empty: boolean;
};

const RestaurantPage = () => {
  const { id } = useParams<{ id: string }>();
  const [locationData, setLocationData] = useState<LocationData | null>(null);
  const [specialtyDishes, setSpecialtyDishes] = useState<Dish[]>([]);
  const [feedbackResponse, setFeedbackResponse] =
    useState<FeedbackResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [dishesLoading, setDishesLoading] = useState(true);
  const [feedbacksLoading, setFeedbacksLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dishesError, setDishesError] = useState<string | null>(null);
  const [feedbacksError, setFeedbacksError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("service");
  const [sortBy, setSortBy] = useState<string>("rate,desc");
  const [currentPage, setCurrentPage] = useState<number>(0);
  const [pageSize] = useState<number>(4);

  useEffect(() => {
    const fetchLocationData = async () => {
      if (!id) {
        setError("Location ID is required");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${getApiBaseUrl()}/locations/${id}`);

        if (!response.ok) {
          throw new Error(`Failed to fetch location data: ${response.status}`);
        }

        const data = await response.json();
        setLocationData(data);
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : "Failed to fetch location data";
        setError(errorMessage);
        console.error("Error fetching location data:", error);
      } finally {
        setLoading(false);
      }
    };

    const fetchSpecialtyDishes = async () => {
      if (!id) {
        setDishesError("Location ID is required");
        setDishesLoading(false);
        return;
      }

      try {
        setDishesLoading(true);
        setDishesError(null);
        const response = await fetch(
          `${getApiBaseUrl()}/locations/${id}/speciality-dishes`,
        );

        if (!response.ok) {
          throw new Error(
            `Failed to fetch specialty dishes: ${response.status}`,
          );
        }

        const data = await response.json();
        setSpecialtyDishes(data);
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : "Failed to fetch specialty dishes";
        setDishesError(errorMessage);
        console.error("Error fetching specialty dishes:", error);
      } finally {
        setDishesLoading(false);
      }
    };

    fetchLocationData();
    fetchSpecialtyDishes();
  }, [id]);

  useEffect(() => {
    const fetchFeedbacks = async () => {
      if (!id) {
        setFeedbacksError("Location ID is required");
        setFeedbacksLoading(false);
        return;
      }

      try {
        setFeedbacksLoading(true);
        setFeedbacksError(null);

        const params = new URLSearchParams({
          type: activeTab,
          sort: sortBy,
          page: currentPage.toString(),
          size: pageSize.toString(),
        });

        const response = await fetch(
          `${getApiBaseUrl()}/locations/${id}/feedbacks?${params}`,
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch feedbacks: ${response.status}`);
        }

        const data = await response.json();
        setFeedbackResponse(data);
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Failed to fetch feedbacks";
        setFeedbacksError(errorMessage);
        console.error("Error fetching feedbacks:", error);
      } finally {
        setFeedbacksLoading(false);
      }
    };

    fetchFeedbacks();
  }, [id, activeTab, sortBy, currentPage, pageSize]);

  const locationName = locationData?.name || "Green & Tasty";
  const locationAddress = locationData?.address || "Neka lokacija";
  const locationRating = locationData?.rating || 4.73;
  const locationDescription = locationData?.description || "";

  const defaultDescription = [
    "Located on bustling Rustaveli Avenue, this branch offers a perfect mix of city energy and a cozy atmosphere.",
    "Known for our fresh, locally sourced dishes, we focus on health and sustainability, featuring Georgian cuisine with a modern twist. The menu includes vegetarian and vegan options, along with exclusive seasonal specials.",
    "With its spacious outdoor terrace, this location is ideal for both casual lunches and intimate dinners.",
  ];

  const descriptionParagraphs = locationDescription
    ? locationDescription.split("\n").filter((p) => p.trim())
    : defaultDescription;

  const handleSortChange = (newSort: string) => {
    const sortMapping: Record<string, string> = {
      "top-rated-first": "rate,desc",
      "low-rated-first": "rate,asc",
      "newest-first": "date,desc",
      "oldest-first": "date,asc",
    };

    const sortParam = sortMapping[newSort] || "rate,desc";
    setSortBy(sortParam);
    setCurrentPage(0);
  };

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setCurrentPage(0);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const generatePageNumbers = () => {
    if (!feedbackResponse) return [];
    const totalPages = feedbackResponse.totalPages;
    const pages = [];
    for (let i = 0; i < Math.min(totalPages, 3); i++) {
      pages.push(i);
    }
    return pages;
  };

  return (
    <>
      <Header />
      <div className="max-w-[1440px] px-10 mx-auto flex flex-col gap-16 mb-7 font-poppins">
        <section className="flex gap-2 mt-2 font-light text-[14px] leading-[24px] tracking-normal">
          <Link
            to="/"
            className="cursor-pointer hover:text-[var(--color-brand)] transition-colors"
          >
            Main page
          </Link>
          <span>{">"}</span>

          <span className="font-medium text-[14px] leading-[24px]">
            Location {locationAddress}
          </span>
        </section>

        <section className="flex gap-20">
          <div className="flex flex-col gap-6">
            <h1 className="font-medium text-5xl leading-[48px] tracking-normal align-middle">
              {locationName}
            </h1>
            <div className="flex justify-between">
              <p className="flex items-center gap-1">
                <span>
                  <img src={location_icon} alt="Location icon" />
                </span>
                <span>{locationAddress}</span>
              </p>
              <p className="flex items-center gap-1">
                <span>{locationRating}</span>
                <span>
                  <img src={star_icon} alt="Star icon" />
                </span>
              </p>
            </div>
            <div className="max-w-[339px] flex flex-col gap-3">
              {loading ? (
                <>
                  <div className="bg-gray-200 h-4 rounded animate-pulse"></div>
                  <div className="bg-gray-200 h-4 rounded animate-pulse"></div>
                  <div className="bg-gray-200 h-4 rounded w-3/4 animate-pulse"></div>
                </>
              ) : error ? (
                <>
                  {defaultDescription.map((paragraph, index) => (
                    <p key={index}>{paragraph}</p>
                  ))}
                </>
              ) : (
                descriptionParagraphs.map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))
              )}
            </div>
            <Link
              to="/book-table"
              className="mt-4 py-4 font-bold text-sm leading-6 tracking-normal text-center align-middle justify-between p-2 pr-4 pl-4 rounded-[8px] opacity-100 bg-[var(--color-brand)] text-white"
            >
              Book a Table
            </Link>
          </div>
          <div className="flex-1">
            <img
              src={locationData?.image || locationImg}
              alt="Location"
              className="object-cover h-full rounded-[24px]"
              onError={(e) => {
                e.currentTarget.src = locationImg;
              }}
            />
          </div>
        </section>

        <section className="flex flex-col gap-10">
          <h2 className="font-medium text-[24px] leading-[40px] align-middle">
            Specialty Dishes
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
                  Error loading specialty dishes: {dishesError}
                </p>
              </div>
            ) : specialtyDishes.length > 0 ? (
              specialtyDishes
                .slice(0, 4)
                .map((dish) => <DiscCard key={dish.id} dish={dish} />)
            ) : (
              <div className="col-span-4 text-center py-8">
                <p className="text-gray-500">No specialty dishes available</p>
              </div>
            )}
          </div>
        </section>

        <section className="flex flex-col gap-10">
          <h2 className="font-medium text-[24px] leading-[40px] tracking-normal align-middle">
            Customer Reviews
          </h2>
          <div className="flex flex-col gap-6">
            <div className="flex justify-between items-center">
              <div
                className="border-b border-b-[#dadada] font-medium text-[18px] leading-[32
px] tracking-normal flex gap-2 pr-2"
              >
                <button
                  className={`py-2 cursor-pointer hover:text-[var(--color-brand)] ${
                    activeTab === "service"
                      ? "text-[var(--color-brand)] border-b-2 border-[var(--color-brand)]"
                      : ""
                  }`}
                  onClick={() => handleTabChange("service")}
                >
                  Service
                </button>
                <button
                  className={`py-2 cursor-pointer hover:text-[var(--color-brand)] ${
                    activeTab === "cuisine"
                      ? "text-[var(--color-brand)] border-b-2 border-[var(--color-brand)]"
                      : ""
                  }`}
                  onClick={() => handleTabChange("cuisine")}
                >
                  Cuisine experience
                </button>
              </div>
              <div className="flex gap-4 items-center">
                <p>Sort by:</p>
                <select
                  name="sort"
                  id="sort"
                  onChange={(e) => handleSortChange(e.target.value)}
                  className="px-2 py-1 text-[var(--color-brand)] border border-[var(--color-brand)] rounded-lg align-middle"
                >
                  <option value="top-rated-first">Top Rated First</option>
                  <option value="low-rated-first">Low Rated First</option>
                  <option value="newest-first">Newest First</option>
                  <option value="oldest-first">Oldest First</option>
                </select>
              </div>
            </div>
            <div className="flex gap-8">
              {feedbacksLoading ? (
                Array.from({ length: 4 }).map((_, index) => (
                  <div
                    key={`feedback-loading-${index}`}
                    className="flex flex-col shadow-[0px_0px_10px_4px_#DADADAB2] rounded-3xl animate-pulse"
                  >
                    <div className="p-6 flex justify-between items-center gap-3">
                      <div className="w-[60px] h-[60px] bg-gray-200 rounded-full"></div>
                      <div className="flex-1">
                        <div className="bg-gray-200 h-4 rounded mb-2"></div>
                        <div className="bg-gray-200 h-3 rounded w-1/2"></div>
                      </div>
                    </div>
                    <div className="px-6 pb-6">
                      <div className="bg-gray-200 h-4 rounded mb-2"></div>
                      <div className="bg-gray-200 h-4 rounded mb-2"></div>
                      <div className="bg-gray-200 h-4 rounded w-3/4"></div>
                    </div>
                  </div>
                ))
              ) : feedbacksError ? (
                <div className="col-span-4 text-center py-8">
                  <p className="text-red-500 mb-4">
                    Error loading feedbacks: {feedbacksError}
                  </p>
                </div>
              ) : feedbackResponse && feedbackResponse.content.length > 0 ? (
                feedbackResponse.content.map((feedback) => (
                  <FeedbackCard key={feedback.id} feedback={feedback} />
                ))
              ) : (
                <div className="col-span-4 text-center py-8">
                  <p className="text-gray-500">
                    No reviews available for this category
                  </p>
                </div>
              )}
            </div>
          </div>
          {feedbackResponse && !feedbackResponse.empty && (
            <div className="flex gap-2 items-center self-center">
              <button
                className={`cursor-pointer ${feedbackResponse.first ? "hidden" : ""}`}
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={feedbackResponse.first}
              >
                <img
                  src={arrow_right_icon}
                  alt="Previous"
                  style={{ transform: "rotate(180deg)" }}
                />
              </button>
              {generatePageNumbers().map((pageNum) => (
                <button
                  key={pageNum}
                  className="text-center cursor-pointer px-2 pb-1 hover:text-[var(--color-brand)]"
                  style={{
                    borderBottom:
                      pageNum === currentPage
                        ? "1px solid var(--color-brand)"
                        : "none",
                  }}
                  onClick={() => handlePageChange(pageNum)}
                >
                  {pageNum + 1}
                </button>
              ))}
              <button
                className={`cursor-pointer ${feedbackResponse.last ? "hidden" : ""}`}
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={feedbackResponse.last}
              >
                <img src={arrow_right_icon} alt="Next" />
              </button>
            </div>
          )}
        </section>
      </div>
    </>
  );
};

export default RestaurantPage;
