// import Layout from "../../components/layout";

import Header from "../../components/header";
import section_image from "../../assets/home/section-image.png";
import DiscCard from "./components/DishCard";
import Layout from "../../components/layout";
import LocationCard from "./components/LocationCard";

const HomePage = () => {
  return (
    <>
      <Header />
      <section
        className="relative flex justify-start font-poppins"
        style={{
          backgroundImage: `url(${section_image})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="max-w-[1440px] w-full mx-auto flex">
          {/* <img src={section_image} alt="Section Image" className="w-full -z-10 absolute top-0 left-0 right-0 bottom-0" /> */}
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
            <button className="pt-3.5 rotate-0 opacity-100 rounded-[8px] bg-[var(--color-brand)] text-white hover:bg-[#009a0b] py-4 text-center">
              View Menu
            </button>
          </div>
        </div>
      </section>
      <Layout>
        <section className="flex flex-col gap-10">
          <h2 className="font-medium text-[24px] leading-[40px] align-middle">
            Most popular Dishes
          </h2>
          <div className="grid grid-cols-4 gap-8">
            {Array.from({ length: 4 }).map((_, index) => (
              <DiscCard key={index} />
            ))}
          </div>
        </section>
        <section className="flex flex-col gap-10">
          <h2 className="font-medium text-[24px] leading-[40px] align-middle">
            Locations
          </h2>
          <div className="grid grid-cols-3 gap-8">
            {Array.from({ length: 3 }).map((_, index) => (
              <LocationCard key={index} />
            ))}
          </div>
        </section>
      </Layout>
    </>
  );
};

export default HomePage;
