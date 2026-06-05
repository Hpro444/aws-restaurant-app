import { useState } from "react";
import clock_icon from "../../../assets/availableTables/Clock.png";
import location from "../../../assets/availableTables/location.png";
import location_icon from "../../../assets/availableTables/location-icon.png";
import plus_icon from "../../../assets/availableTables/plus-icon.png";
import { type TableResult, type AvailableSlot } from "../../../types/location";
import AvailableSlotsModal from "./AvailableSlotsModal";
import MakeReservationModal from "./MakeReservationModal";
import { formatDate, formatSlotTime } from "../../../utils/reservationHelpers";

const SLOTS_PREVIEW = 4;

type SlotButtonProps = {
  slot: AvailableSlot;
  onClick: () => void;
};

const SlotButton = ({ slot, onClick }: SlotButtonProps) => {
  return (
    <button
      onClick={onClick}
      className="font-medium text-[14px] leading-[24px] align-middle border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer hover:bg-green-50"
    >
      <img src={clock_icon} alt="Clock icon" className="w-4 h-4" />
      <span>
        {formatSlotTime(slot.start_time)} - {formatSlotTime(slot.end_time)}
      </span>
    </button>
  );
};

type CardProps = {
  table: TableResult;
  locationAddress: string;
  locationId: string;
  date: string;
  initialGuests?: number;
};

const Card = ({
  table,
  locationId,
  locationAddress,
  date,
  initialGuests = 1,
}: CardProps) => {
  const [isSlotsModalOpen, setIsSlotsModalOpen] = useState(false);
  const [isMakeReservationOpen, setIsMakeReservationOpen] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);

  const slots = table.available_slots.slice(0, SLOTS_PREVIEW);
  const hasMore = table.available_slots.length > SLOTS_PREVIEW;

  const handlePreviewSlotClick = (slot: AvailableSlot) => {
    setSelectedSlot(slot);
    setIsMakeReservationOpen(true);
  };

  const handleShowAllClick = () => {
    setIsSlotsModalOpen(true);
  };

  const handleSlotSelectFromModal = (slot: AvailableSlot) => {
    setSelectedSlot(slot);
    setIsSlotsModalOpen(false);
    setIsMakeReservationOpen(true);
  };

  const handleCloseMakeReservation = () => {
    setIsMakeReservationOpen(false);
  };

  return (
    <>
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
              <img
                src={location_icon}
                alt="Location icon"
                className="w-4 h-4"
              />
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
                <SlotButton
                  key={slot.slot_id}
                  slot={slot}
                  onClick={() => handlePreviewSlotClick(slot)}
                />
              ))}

              {hasMore && (
                <button
                  onClick={handleShowAllClick}
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

      {isSlotsModalOpen && (
        <AvailableSlotsModal
          slots={table.available_slots}
          locationAddress={locationAddress}
          tableNumber={table.table_number}
          date={date}
          onSelectSlot={handleSlotSelectFromModal}
          onClose={() => setIsSlotsModalOpen(false)}
        />
      )}

      {isMakeReservationOpen && selectedSlot && (
        <MakeReservationModal
          slot={selectedSlot}
          allSlots={table.available_slots}
          locationAddress={locationAddress}
          locationId={locationId}
          tableNumber={table.table_number}
          tableCapacity={table.capacity}
          date={date}
          initialGuests={initialGuests}
          onClose={handleCloseMakeReservation}
          onSelectSlot={setSelectedSlot}
          onReservationResult={(result) => {
            if (result.ok) {
              console.log("Reservation created:", result.data);
            } else {
              console.error("Reservation failed:", result.message);
            }
          }}
        />
      )}
    </>
  );
};

export default Card;
