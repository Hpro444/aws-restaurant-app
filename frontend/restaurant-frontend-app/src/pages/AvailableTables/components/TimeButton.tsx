import { useState } from "react";

import clock_icon from "../../../assets/availableTables/Clock.png";
import arrow_down from "../../../assets/restaurant/arrow-down-icon.png";

const TimeButton = () => {
  const [isTimeOpen, setIsTimeOpen] = useState(false);
  const [selectedTime, setSelectedTime] = useState("");

  return (
    <div className="relative w-full max-w-[200px]">
      <div className="border-2 rounded-lg overflow-hidden h-full">
        <button
          onClick={() => setIsTimeOpen(!isTimeOpen)}
          className="w-full cursor-pointer flex items-center justify-between px-6 py-4 bg-white hover:bg-gray-50"
        >
          <div className="flex items-center gap-2">
            <img src={clock_icon} alt="Clock icon" className="w-6 h-6" />
            <span className="text-gray-800">{selectedTime || "Time"}</span>
          </div>
          <img
            src={arrow_down}
            alt="Arrow icon"
            className={`h-6 w-6 transition-transform ${isTimeOpen ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      {isTimeOpen && (
        <ul className="absolute w-full mt-1 border border-gray-200 rounded-lg overflow-hidden bg-white text-black z-10">
          {["10:00", "12:00", "14:00", "16:00", "18:00", "20:00"].map(
            (time) => (
              <li
                key={time}
                onClick={() => {
                  setSelectedTime(time);
                  setIsTimeOpen(false);
                }}
                className={`font-medium text-sm leading-6 tracking-normal align-middle px-2 py-1 cursor-pointer border-b border-gray-100 last:border-b-0 ${
                  selectedTime === time ? "bg-green-100" : "hover:bg-gray-50"
                }`}
              >
                {time}
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
};

export default TimeButton;
