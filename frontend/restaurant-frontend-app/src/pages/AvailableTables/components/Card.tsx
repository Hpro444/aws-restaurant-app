import { useState } from "react";
import clock_icon from "../../../assets/availableTables/Clock.png";
import location from "../../../assets/availableTables/location.png";
import location_icon from "../../../assets/availableTables/location-icon.png";
import plus_icon from "../../../assets/availableTables/plus-icon.png";
import {
  type TableResult,
  type AvailableSlot,
} from "../availableTables.services";

const SLOTS_PREVIEW = 4;

const formatSlotTime = (iso: string): string => {
  const match = iso.match(/T(\d{2}:\d{2})/);
  return match ? match[1] : iso;
};

const formatDate = (yyyy_mm_dd: string): string => {
  const d = new Date(yyyy_mm_dd + "T00:00:00");
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const SlotButton = ({ slot }: { slot: AvailableSlot }) => (
  <button className="font-medium text-[14px] leading-[24px] align-middle border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer hover:bg-green-50">
    <img src={clock_icon} alt="Clock icon" className="w-4 h-4" />
    <span>
      {formatSlotTime(slot.start_time)} - {formatSlotTime(slot.end_time)}
    </span>
  </button>
);

type CardProps = {
  table: TableResult;
  locationAddress: string;
  date: string;
};

const Card = ({ table, locationAddress, date }: CardProps) => {
  const [showAll, setShowAll] = useState(false);

  const slots = showAll
    ? table.available_slots
    : table.available_slots.slice(0, SLOTS_PREVIEW);

  const hasMore = table.available_slots.length > SLOTS_PREVIEW;

  return (
    <div className="max-w-[664px] flex rounded-3xl shadow-[0px_0px_10px_4px_#DADADAB2] font-medium text-[14px] leading-[24px] tracking-normal align-middle">
      <div>
        <img
          src={location}
          alt="Restaurant"
          className="w-full h-full object-cover rounded-l-3xl max-w-[200px]"
        />
      </div>
      <div className="flex-1 flex flex-col gap-4 p-6">
        <div className="flex justify-between items-center">
          <p className="flex gap-1 items-center font-medium text-[14px] leading-[24px] tracking-normal align-middle">
            <img src={location_icon} alt="Location icon" className="w-4 h-4" />
            {locationAddress}
          </p>
          <p>Table {table.table_number}</p>
        </div>
        <p>Table seating capacity: {table.capacity} people</p>
        <div className="flex flex-col gap-3">
          <p>
            {table.available_slots.length}{" "}
            {table.available_slots.length === 1 ? "slot" : "slots"} available
            for {formatDate(date)}:
          </p>
          <div className="grid grid-cols-2 gap-2">
            {slots.map((slot) => (
              <SlotButton key={slot.slot_id} slot={slot} />
            ))}
            {!showAll && hasMore && (
              <button
                onClick={() => setShowAll(true)}
                className="font-medium text-[14px] leading-[24px] align-middle justify-self-start border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer hover:bg-green-50"
              >
                <img src={plus_icon} alt="Plus icon" className="w-4 h-4" />
                <span>Show all</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Card;
