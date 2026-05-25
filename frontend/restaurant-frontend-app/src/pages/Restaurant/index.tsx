import Header from "../../components/header";
import locationImg from "../../assets/restaurant/location.png";
import DiscCard from "../../components/common/DishCard";
// import Layout from "../../components/layout";
import userAvatar from "../../assets/restaurant/user-image.png";
import star_icon from "../../assets/restaurant/star-icon.png";
import location_icon from "../../assets/restaurant/location-icon.png";
import arrow_right_icon from "../../assets/restaurant/arrow-right-icon.png";

const RestaurantPage = () => {
  return (
    <>
      <Header />
      {/* <Layout> */}
      <div className="max-w-[1440px] px-10 mx-auto flex flex-col gap-16 mb-7 font-poppins">
        {/* Breadcrumb */}
        <section className="flex gap-2 mt-2 font-light text-[14px] leading-[24px] tracking-normal">
          <span className="cursor-pointer">Main page</span>
          <span>{">"}</span>
          <span className="cursor-pointer font-medium text-[14px] leading-[24px]">
            Location Neka lokacija
          </span>
        </section>
        <section className="flex gap-20">
          <div className="flex flex-col gap-6">
            <h1 className="font-medium text-5xl leading-[48px] tracking-normal align-middle">
              Green & Tasty
            </h1>
            <div className="flex justify-between">
              <p className="flex items-center gap-1">
                <span>
                  <img src={location_icon} alt="Location icon" />
                </span>
                <span>Neka lokacija</span>
              </p>
              <p className="flex items-center gap-1">
                <span>4.73</span>
                <span>
                  <img src={star_icon} alt="Star icon" />
                </span>
              </p>
            </div>
            <div className="max-w-[339px] flex flex-col gap-3">
              <p>
                Located on bustling Rustaveli Avenue, this branch offers a
                perfect mix of city energy and a cozy atmosphere.
              </p>
              <p>
                Known for our fresh, locally sourced dishes, we focus on health
                and sustainability, featuring Georgian cuisine with a modern
                twist. The menu includes vegetarian and vegan options, along
                with exclusive seasonal specials.
              </p>
              <p>
                With its spacious outdoor terrace, this location is ideal for
                both casual lunches and intimate dinners.
              </p>
            </div>
            <button className="mt-4 py-4 font-bold text-sm leading-6 tracking-normal text-center align-middle justify-between p-2 pr-4 pl-4 rounded-[8px] opacity-100 bg-[var(--color-brand)] text-white">
              Book a Table
            </button>
          </div>
          <div className="flex-1">
            <img
              src={locationImg}
              alt="Location"
              className="object-cover h-full rounded-[24px]"
            />
          </div>
        </section>

        <section className="flex flex-col gap-10">
          <h2 className="font-medium text-[24px] leading-[40px] align-middle">
            Specialty Dishes
          </h2>
          <div className="grid grid-cols-4 gap-8">
            {Array.from({ length: 4 }).map((_, index) => (
              <DiscCard key={index} />
            ))}
          </div>
        </section>

        <section className="flex flex-col gap-10">
          <h2 className="font-medium text-[24px] leading-[40px] tracking-normal align-middle">
            Customer Reviews
          </h2>
          {/* Cards */}
          <div className="flex flex-col gap-6">
            <div className="flex justify-between items-center">
              {/* Tabs */}
              <div className="border-b border-b-[#dadada] font-medium text-[18px] leading-[32px] tracking-normal flex gap-2 pr-2">
                <button className="py-2 cursor-pointer hover:text-[var(--color-brand)]">
                  Service
                </button>
                <button className="py-2 cursor-pointer hover:text-[var(--color-brand)]">
                  Cuisine experience
                </button>
              </div>
              {/* Sorting */}
              <div className="flex gap-4 items-center">
                <p>Sort by:</p>
                <select
                  name="sort"
                  id="sort"
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
              {/* Card */}
              <div className="flex flex-col shadow-[0px_0px_10px_4px_#DADADAB2] rounded-3xl">
                <div className="p-6 flex justify-between items-center gap-3">
                  <div className="w-[60px] h-[60px]">
                    <img
                      src={userAvatar}
                      alt="User Avatar"
                      className="rounded-[50%] object-cover w-full h-full"
                    />
                  </div>
                  <div className="flex justify-between flex-1">
                    <div className="font-medium text-[14px] leading-[24px] tracking-normal">
                      <p>Anna</p>
                      <p className="font-light text-[12px] leading-[16px]">
                        6/8/2024
                      </p>
                    </div>
                    <p className="flex gap-1">
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                    </p>
                  </div>
                </div>
                <div className="flex-1 px-6 pb-6">
                  <p className="max-w-[268px] font-poppins font-light text-[14px] leading-[24px] tracking-normal">
                    Absolutely loved this restaurant! The outdoor terrace was
                    perfect for a relaxing evening, and the menu had so many
                    fresh, healthy options. I’m vegetarian, and it’s great to
                    see so many plant-based dishes with authentic Georgian
                    flavors. Definitely coming back soon!
                  </p>
                </div>
              </div>
              {/* Card */}
              <div className="flex flex-col shadow-[0px_0px_10px_4px_#DADADAB2] rounded-3xl">
                <div className="p-6 flex justify-between items-center gap-3">
                  <div className="w-[60px] h-[60px]">
                    <img
                      src={userAvatar}
                      alt="User Avatar"
                      className="rounded-[50%] object-cover w-full h-full"
                    />
                  </div>
                  <div className="flex justify-between flex-1">
                    <div className="font-medium text-[14px] leading-[24px] tracking-normal">
                      <p>Anna</p>
                      <p className="font-light text-[12px] leading-[16px]">
                        6/8/2024
                      </p>
                    </div>
                    <p className="flex gap-1">
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                    </p>
                  </div>
                </div>
                <div className="flex-1 px-6 pb-6">
                  <p className="max-w-[268px] font-poppins font-light text-[14px] leading-[24px] tracking-normal">
                    Absolutely loved this restaurant! The outdoor terrace was
                    perfect for a relaxing evening, and the menu had so many
                    fresh, healthy options. I’m vegetarian, and it’s great to
                    see so many plant-based dishes with authentic Georgian
                    flavors. Definitely coming back soon!
                  </p>
                </div>
              </div>
              {/* Card */}
              <div className="flex flex-col shadow-[0px_0px_10px_4px_#DADADAB2] rounded-3xl">
                <div className="p-6 flex justify-between items-center gap-3">
                  <div className="w-[60px] h-[60px]">
                    <img
                      src={userAvatar}
                      alt="User Avatar"
                      className="rounded-[50%] object-cover w-full h-full"
                    />
                  </div>
                  <div className="flex justify-between flex-1">
                    <div className="font-medium text-[14px] leading-[24px] tracking-normal">
                      <p>Anna</p>
                      <p className="font-light text-[12px] leading-[16px]">
                        6/8/2024
                      </p>
                    </div>
                    <p className="flex gap-1">
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                    </p>
                  </div>
                </div>
                <div className="flex-1 px-6 pb-6">
                  <p className="max-w-[268px] font-poppins font-light text-[14px] leading-[24px] tracking-normal">
                    Absolutely loved this restaurant! The outdoor terrace was
                    perfect for a relaxing evening, and the menu had so many
                    fresh, healthy options. I’m vegetarian, and it’s great to
                    see so many plant-based dishes with authentic Georgian
                    flavors. Definitely coming back soon!
                  </p>
                </div>
              </div>
              {/* Card */}
              <div className="flex flex-col shadow-[0px_0px_10px_4px_#DADADAB2] rounded-3xl">
                <div className="p-6 flex justify-between items-center gap-3">
                  <div className="w-[60px] h-[60px]">
                    <img
                      src={userAvatar}
                      alt="User Avatar"
                      className="rounded-[50%] object-cover w-full h-full"
                    />
                  </div>
                  <div className="flex justify-between flex-1">
                    <div className="font-medium text-[14px] leading-[24px] tracking-normal">
                      <p>Anna</p>
                      <p className="font-light text-[12px] leading-[16px]">
                        6/8/2024
                      </p>
                    </div>
                    <p className="flex gap-1">
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                      <span>
                        <img src={star_icon} alt="Star" />
                      </span>
                    </p>
                  </div>
                </div>
                <div className="flex-1 px-6 pb-6">
                  <p className="max-w-[268px] font-poppins font-light text-[14px] leading-[24px] tracking-normal">
                    Absolutely loved this restaurant! The outdoor terrace was
                    perfect for a relaxing evening, and the menu had so many
                    fresh, healthy options. I’m vegetarian, and it’s great to
                    see so many plant-based dishes with authentic Georgian
                    flavors. Definitely coming back soon!
                  </p>
                </div>
              </div>
            </div>
          </div>
          {/* Pagination */}
          <div className="flex gap-2 items-center self-center">
            <button className="cursor-pointer hidden">
              <img src={arrow_right_icon} alt="Next" />
            </button>
            {[...Array(3)].map((_, i) => (
              <button
                key={i}
                className="text-center cursor-pointer px-2 pb-1 hover:text-[var(--color-brand)]"
                style={{
                  borderBottom:
                    i == 0 ? "1px solid var(--color-brand)" : "none",
                }}
              >
                {i + 1}
              </button>
            ))}
            <button className="cursor-pointer">
              <img src={arrow_right_icon} alt="Next" />
            </button>
          </div>
        </section>
      </div>
      {/* </Layout> */}
    </>
  );
};

export default RestaurantPage;
