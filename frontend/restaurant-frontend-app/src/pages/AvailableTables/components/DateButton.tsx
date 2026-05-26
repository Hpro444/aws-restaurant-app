import { useState } from "react";

import calendar_icon from "../../../assets/availableTables/Calendar.png";
import arrow_down from "../../../assets/restaurant/arrow-down-icon.png";

type DateButtonProps = {
  value: string;
  onChange: (date: string) => void;
};

const generateDates = () =>
  Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    const value = d.toISOString().split("T")[0];
    const label =
      i === 0
        ? "Today"
        : i === 1
          ? "Tomorrow"
          : d.toLocaleDateString("en-US", {
              weekday: "short",
              month: "short",
              day: "numeric",
            });
    return { label, value };
  });

const dates = generateDates();

const DateButton = ({ value, onChange }: DateButtonProps) => {
  const [isOpen, setIsOpen] = useState(false);

  const selected = dates.find((d) => d.value === value);

  return (
    <div className="relative w-full max-w-[200px]">
      <div className="border-2 rounded-lg overflow-hidden h-full">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full cursor-pointer flex items-center justify-between px-6 py-4 bg-white hover:bg-gray-50"
        >
          <div className="flex items-center gap-2">
            <img src={calendar_icon} alt="Calendar icon" className="w-6 h-6" />
            <span className="text-gray-800">{selected ? selected.label : "Date"}</span>
          </div>
          <img
            src={arrow_down}
            alt="Arrow icon"
            className={`h-6 w-6 transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      {isOpen && (
        <ul className="absolute w-full mt-1 border border-gray-200 rounded-lg overflow-hidden bg-white text-black z-10">
          {dates.map((date) => (
            <li
              key={date.value}
              onClick={() => {
                onChange(date.value);
                setIsOpen(false);
              }}
              className={`font-medium text-sm leading-6 tracking-normal align-middle px-2 py-1 cursor-pointer border-b border-gray-100 last:border-b-0 ${
                value === date.value ? "bg-green-100" : "hover:bg-gray-50"
              }`}
            >
              {date.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default DateButton;
