import { useState } from "react";
import location_icon from "../../../assets/availableTables/location-icon.png";
import arrow_down from "../../../assets/restaurant/arrow-down-icon.png";
import { LOCATIONS } from "../availableTables.config";

type LocationButtonProps = {
  value: string;
  onChange: (locationId: string) => void;
};

const LocationButton = ({ value, onChange }: LocationButtonProps) => {
  const [isOpen, setIsOpen] = useState(false);

  const selected = LOCATIONS.find((l) => l.id === value);

  return (
    <div className="relative w-full max-w-[400px]">
      <div className="border-2 rounded-lg overflow-hidden h-full">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full cursor-pointer flex items-center justify-between px-6 py-4 bg-white hover:bg-gray-50"
        >
          <div className="flex items-center gap-2">
            <img src={location_icon} alt="Location icon" className="w-6 h-6" />
            <span className="text-gray-800">
              {selected ? selected.name : "Location"}
            </span>
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
          {LOCATIONS.map((location) => (
            <li
              key={location.id}
              onClick={() => {
                onChange(location.id);
                setIsOpen(false);
              }}
              className={`font-medium text-sm leading-6 tracking-normal align-middle px-2 py-1 cursor-pointer border-b border-gray-100 last:border-b-0 ${
                value === location.id ? "bg-green-100" : "hover:bg-gray-50"
              }`}
            >
              {location.name} — {location.address}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default LocationButton;
