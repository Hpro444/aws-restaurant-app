import { useState } from "react";

import clock_icon from "../../../assets/availableTables/Clock.png";
import arrow_down from "../../../assets/restaurant/arrow-down-icon.png";

type TimeButtonProps = {
  value: string;
  style?: React.CSSProperties;
  onChange: (time: string) => void;
};

const TIME_OPTIONS = Array.from({ length: 18 }, (_, i) => {
  const hour = i + 6;
  return String(hour).padStart(2, "0") + ":00";
});

const TimeButton = ({ value, style, onChange }: TimeButtonProps) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative w-full max-w-[200px]" style={style}>
      <div className="border-2 border-[#dadada] rounded-lg overflow-hidden h-full">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full cursor-pointer flex items-center justify-between px-6 py-4 bg-white hover:bg-gray-50"
        >
          <div className="flex items-center gap-2">
            <img src={clock_icon} alt="Clock icon" className="w-6 h-6" />
            <span className="text-gray-800">{value || "Time"}</span>
          </div>
          <img
            src={arrow_down}
            alt="Arrow icon"
            className={`h-6 w-6 transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      {isOpen && (
        <ul className="absolute w-full mt-1 border border-gray-200 rounded-lg overflow-hidden overflow-y-auto max-h-56 bg-white text-black z-10">
          {TIME_OPTIONS.map((time) => (
            <li
              key={time}
              onClick={() => {
                onChange(time);
                setIsOpen(false);
              }}
              className={`font-medium text-sm leading-6 tracking-normal align-middle px-2 py-1 cursor-pointer border-b border-gray-100 last:border-b-0 ${
                value === time ? "bg-green-100" : "hover:bg-gray-50"
              }`}
            >
              {time}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default TimeButton;
