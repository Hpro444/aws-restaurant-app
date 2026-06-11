import { useState } from "react";
import { type TableResult, type AvailableSlot } from "../../../types/location";
import AvailableSlotsModal from "./AvailableSlotsModal";
import MakeReservationModal from "./MakeReservationModal";
import { formatDate } from "../../../utils/reservationHelpers";
import SlotButton, { SLOTS_PREVIEW } from "./SlotButton";
import location from "../../../assets/availableTables/location.png";

type CardProps = {
  table: TableResult;
  locationAddress?: string;
  locationId: string;
  date: string;
  initialGuests?: number;
};

const Card = ({ table, date, initialGuests = 1, locationId }: CardProps) => {
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
              <span className="pi pi-map-marker text-lg" />
              {table.location_address}
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
                  <span className="pi pi-plus text-lg" />
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
          locationAddress={table.location_address}
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
          locationId={locationId}
          locationAddress={table.location_address}
          tableNumber={table.table_number}
          tableCapacity={table.capacity}
          initialGuests={initialGuests}
          date={date}
          onClose={handleCloseMakeReservation}
          onSelectSlot={setSelectedSlot}
        />
      )}
    </>
  );
};

export default Card;
