import no_tables from "../../../assets/availableTables/no-tables-icon.png";

import {Link} from "react-router-dom";

const NoResults = () => {
  return (
    <section className="flex flex-col gap-10 justify-center text-center mx-auto">
      <img
        src={no_tables}
        alt="No tables available"
        className="max-w-[135px] mx-auto"
      />
      <div className="flex flex-col gap-6">
        <div className="max-w-[333px]">
          <h3 className="font-medium text-[18px] leading-[32px] tracking-normal text-center align-middle">
            No Reservations
          </h3>
          <p className=" font-light text-[14px] leading-[24px] tracking-normal text-center align-middle">
            Looks like you haven’t made any reservations yet.
          </p>
        </div>
        <Link to="/book-table" className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors">
          Book a Table
        </Link>
      </div>
    </section>
  );
};

export default NoResults;
