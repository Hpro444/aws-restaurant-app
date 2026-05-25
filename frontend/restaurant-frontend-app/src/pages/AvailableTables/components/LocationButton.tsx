import { useState } from "react";
import location_icon from "../../../assets/availableTables/location-icon.png";
import arrow_down from "../../../assets/restaurant/arrow-down-icon.png";

const LocationButton = () => {
  const [isLocationOpen, setIsLocationOpen] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState("");

  return (
    <div className="relative w-full max-w-[400px]">
      <div className="border-2 rounded-lg overflow-hidden h-full">
        <button
          onClick={() => setIsLocationOpen(!isLocationOpen)}
          className="w-full cursor-pointer flex items-center justify-between px-6 py-4 bg-white hover:bg-gray-50"
        >
          <div className="flex items-center gap-2">
            <img src={location_icon} alt="Location icon" className="w-6 h-6" />
            <span className="text-gray-800">
              {selectedLocation || "Location"}
            </span>
          </div>
          <img
            src={arrow_down}
            alt="Arrow icon"
            className={`h-6 w-6 transition-transform ${isLocationOpen ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      {isLocationOpen && (
        <ul className="absolute w-full mt-1 border border-gray-200 rounded-lg overflow-hidden bg-white text-black z-10">
          {["Adresa 1", "Adresa 2", "Adresa 3"].map((location) => (
            <li
              key={location}
              onClick={() => {
                setSelectedLocation(location);
                setIsLocationOpen(false);
              }}
              className={`font-medium text-sm leading-6 tracking-normal align-middle px-2 py-1 cursor-pointer border-b border-gray-100 last:border-b-0 ${
                selectedLocation === location
                  ? "bg-green-100"
                  : "hover:bg-gray-50"
              }`}
            >
              {location}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default LocationButton;
