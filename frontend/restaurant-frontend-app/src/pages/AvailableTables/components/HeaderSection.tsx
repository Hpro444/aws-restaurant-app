import section_image from "../../../assets/home/section-image.png";
import LocationButton from "./LocationButton";
import DateButton from "./DateButton";
import TimeButton from "./TimeButton";
import GuestsButton from "./GuestsButton";

const HeaderSection = () => {
  return (
    <section
      className="relative flex justify-start font-poppins"
      style={{
        backgroundImage: `url(${section_image})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      <div className="max-w-[1440px] w-full mx-auto flex flex-col text-white gap-[22px] px-10 py-[100px]">
        <h2 className="text-[var(--color-brand)] font-medium text-[24px] leading-[40px] tracking-normal align-middle">
          Green & Tasty Restaurants
        </h2>
        <div className="flex flex-col gap-10">
          <h1 className="font-medium text-[48px] leading-[48px] tracking-normal align-middle text-[var(--color-brand)]">
            Book a Table
          </h1>
          <div className="flex gap-4 max-h-[56px]">
            <LocationButton />
            <DateButton />
            <TimeButton />
            <GuestsButton />

            <button className="py-4 text-center cursor-pointer bg-[var(--color-brand)] text-white w-full max-w-[252px] rounded-lg hover:bg-[#009a0b]">
              Find a Table
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeaderSection;
