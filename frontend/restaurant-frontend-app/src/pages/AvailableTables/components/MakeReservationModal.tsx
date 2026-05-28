import people_icon from "../../../assets/people_green_icon.png";
import minus_icon from "../../../assets/availableTables/minus-icon.png";
import plus_icon from "../../../assets/availableTables/plus-icon.png";
import close_icon from "../../../assets/close_icon.png";
import TimeButton from "./TimeButton";

const MakeReservationModal = () => {
  return (
    <div className="z-50 absolute top-6/12 left-6/12 transform -translate-x-1/2 -translate-y-1/2 flex flex-col max-w-[496px] rounded-[24px] p-6 gap-10 shadow-[0_0_10px_4px_#DADADAB2] bg-[#F7F7F7]">
      <div>
        <div className="flex justify-between items-center">
          <h2 className="font-medium text-2xl leading-[40px] align-middle tracking-normal">
            Make a Reservation
          </h2>
          <button>
            <img src={close_icon} alt="Close" />
          </button>
        </div>
        <p className="font-light text-sm leading-[24px] tracking-normal max-w-[416px]">
          There are{" "}
          <span className="font-medium text-sm leading-[24px] tracking-normal">
            6 slots
          </span>{" "}
          available at{" "}
          <span className="font-medium text-sm leading-[24px] tracking-normal">
            48 Rustaveli Avenue
          </span>
          ,{" "}
          <span className="font-medium text-sm leading-[24px] tracking-normal">
            Table 1
          </span>
          , for{" "}
          <span className="font-medium text-sm leading-[24px] tracking-normal">
            October 14, 2024
          </span>
        </p>
      </div>
      <div className="flex flex-col gap-8">
        <div className="flex flex-col gap-6">
          <div>
            <h3 className="font-medium text-base leading-[32px] align-middle tracking-normal">
              Guests
            </h3>
            <p className="font-light text-sm leading-[24px] align-middle tracking-normal">
              Please specify the number of guests
            </p>
            <p className="font-light text-sm leading-[24px] align-middle tracking-normal">
              Table seating capacity: 10 people
            </p>
          </div>
          <div className="flex justify-between py-4 px-6 border border-[#DADADA] rounded-lg">
            <div className="flex gap-2">
              <img src={people_icon} alt="People icon" className="w-6 h-6" />
              <p className="font-medium text-sm leading-[24px] align-middle tracking-normal text-center">
                Guests
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed">
                <img src={minus_icon} alt="Minus icon" />
              </button>
              <span className="text-gray-800 w-4 text-center">10</span>
              <button className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed">
                <img src={plus_icon} alt="Plus icon" />
              </button>
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h3 className="font-medium text-lg leading-[32px] align-middle tracking-normal">
              Time
            </h3>
            <p className="font-light text-sm leading-[24px] align-middle tracking-normal">
              Please choose your preferred time from the dropdowns below
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <p>From</p>
              <TimeButton
                value="18:00 p.m."
                onChange={(time) => console.log("Selected time:", time)}
                style={{ maxWidth: "none" }}
              />
            </div>
            <div className="flex flex-col gap-1">
              <p>To</p>
              <TimeButton
                value="20:00 p.m."
                onChange={(time) => console.log("Selected time:", time)}
                style={{ maxWidth: "none" }}
              />
            </div>
          </div>
        </div>
      </div>
      <button className="bg-[#00ad0c] text-white rounded-[8px] opacity-100 justify-between py-4 font-bold text-sm leading-[24px] tracking-normal text-center align-middle">
        Make a Reservation
      </button>
    </div>
  );
};

export default MakeReservationModal;
