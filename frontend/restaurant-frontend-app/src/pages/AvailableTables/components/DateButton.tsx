import { useState } from "react";

import calendar_icon from "../../../assets/availableTables/Calendar.png";
import arrow_down from "../../../assets/restaurant/arrow-down-icon.png";

const DateButton = () => {
  const [isDateOpen, setIsDateOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState("");

  return (
    <div className="relative w-full max-w-[200px]">
      <div className="border-2 rounded-lg overflow-hidden h-full">
        <button
          onClick={() => setIsDateOpen(!isDateOpen)}
          className="w-full cursor-pointer flex items-center justify-between px-6 py-4 bg-white hover:bg-gray-50"
        >
          <div className="flex items-center gap-2">
            <img src={calendar_icon} alt="Calendar icon" className="w-6 h-6" />
            <span className="text-gray-800">{selectedDate || "Date"}</span>
          </div>
          <img
            src={arrow_down}
            alt="Arrow icon"
            className={`h-6 w-6 transition-transform ${isDateOpen ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      {isDateOpen && (
        <ul className="absolute w-full mt-1 border border-gray-200 rounded-lg overflow-hidden bg-white text-black z-10">
          {["Today", "Tomorrow", "This Weekend", "Next Week"].map((date) => (
            <li
              key={date}
              onClick={() => {
                setSelectedDate(date);
                setIsDateOpen(false);
              }}
              className={`font-medium text-sm leading-6 tracking-normal align-middle px-2 py-1 cursor-pointer border-b border-gray-100 last:border-b-0 ${
                selectedDate === date ? "bg-green-100" : "hover:bg-gray-50"
              }`}
            >
              {date}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default DateButton;
