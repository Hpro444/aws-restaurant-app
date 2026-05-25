import no_tables from "../../../assets/availableTables/no-tables-icon.png";

const NoResults = () => {
  return (
    <section className="flex flex-col gap-10 justify-center text-center mx-auto">
      <img
        src={no_tables}
        alt="No tables available"
        className="max-w-[333px]"
      />
      <div className="max-w-[333px]">
        <h3 className="font-medium text-[18px] leading-[32px] tracking-normal text-center align-middle">
          No Tables Available
        </h3>
        <p className=" font-light text-[14px] leading-[24px] tracking-normal text-center align-middle">
          Try a different time, adjust the number of guests or explore other
          locations
        </p>
      </div>
    </section>
  );
};

export default NoResults;