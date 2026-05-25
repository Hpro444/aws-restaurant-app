import { useState } from "react";
import people_icon from "../../../assets/availableTables/People.png";
import minus_icon from "../../../assets/availableTables/minus-icon.png";
import plus_icon from "../../../assets/availableTables/plus-icon.png";

const GuestsButton = () => {
  const [numOfGuests, setNumOfGuests] = useState(1);
  
  return (
    <div className="flex items-center gap-2 max-w-[255px] justify-between w-full px-6 py-4 bg-white rounded-lg">
      <div className="flex items-center gap-2">
        <img src={people_icon} alt="Guests icon" />
        <span className="text-gray-800">Guests</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setNumOfGuests(Math.max(0, numOfGuests - 1))}
          className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer"
        >
          <img src={minus_icon} alt="Minus icon" />
        </button>
        <span className="text-gray-800 w-4 text-center">{numOfGuests}</span>
        <button
          onClick={() => setNumOfGuests(numOfGuests + 1)}
          className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer"
        >
          <img src={plus_icon} alt="Plus icon" />
        </button>
      </div>
    </div>
  );
};

export default GuestsButton;
