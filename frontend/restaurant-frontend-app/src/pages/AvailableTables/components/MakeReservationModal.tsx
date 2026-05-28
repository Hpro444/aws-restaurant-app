import people_icon from "../../../assets/availableTables/People.png";
import minus_icon from "../../../assets/availableTables/minus-icon.png";
import plus_icon from "../../../assets/availableTables/plus-icon.png";

const MakeReservationModal = () => {
  return (
    <div className="rotate-0 opacity-100 top-[294px] left-[488px] rounded-[24px] p-6 gap-10">
      <div>
        <div>
          <h2>Make a Reservation</h2>
          <button>
            <img src="#" alt="Close" />
          </button>
        </div>
        <p>
          You are making a reservation at 48 Rustaveli Avenue, Table 1, for
          October 14, 2024
        </p>
      </div>
      <div>
        <div>
          <div>
            <h3>Guests</h3>
            <p>
              Please specify the number of guests. Table seating capacity: 10
              people
            </p>
          </div>
          <div>
            <div>
              <img src={people_icon} alt="People icon" />
              <p>Guests</p>
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
        <div>
          <div>
            <h3>Time</h3>
            <p>Please choose your preferred time from the dropdowns below</p>
          </div>
          <div>
            <div>
              <p>From</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MakeReservationModal;
