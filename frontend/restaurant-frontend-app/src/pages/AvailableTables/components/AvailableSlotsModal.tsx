import clock_icon from "../../../assets/availableTables/Clock.png";
import close_icon from "../../../assets/close_icon.png";
import type { AvailableSlot } from "../../../types/location";
import { formatDate, formatSlotTime } from "../../../utils/reservationHelpers";

type AvailableSlotsModalProps = {
  slots: AvailableSlot[];
  locationAddress: string;
  tableNumber: number;
  date: string;
  onSelectSlot: (slot: AvailableSlot) => void;
  onClose: () => void;
};

const AvailableSlotsModal = ({
  slots,
  locationAddress,
  tableNumber,
  date,
  onSelectSlot,
  onClose,
}: AvailableSlotsModalProps) => {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[520px] rounded-[24px] p-6 gap-8 flex flex-col bg-[#F7F7F7] shadow-[0px_0px_10px_4px_#DADADAB2]"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <div className="flex justify-between items-center">
            <h2 className="font-medium text-2xl leading-[40px] tracking-normal">
              Available slots
            </h2>
            <button onClick={onClose}>
              <img src={close_icon} alt="Close" />
            </button>
          </div>
          <p className="font-light text-sm leading-[24px] tracking-normal">
            There are <span className="font-medium">{slots.length} slots</span>{" "}
            available at <span className="font-medium">{locationAddress}</span>,{" "}
            <span className="font-medium">Table {tableNumber}</span>, for{" "}
            <span className="font-medium">{formatDate(date)}</span>.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 max-h-[320px] overflow-y-auto pr-1">
          {slots.map((slot) => (
            <button
              key={slot.slot_id}
              onClick={() => onSelectSlot(slot)}
              className="font-medium text-[14px] leading-[24px] border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer hover:bg-green-50"
            >
              <img src={clock_icon} alt="Clock icon" className="w-4 h-4" />
              <span>
                {formatSlotTime(slot.start_time)} -{" "}
                {formatSlotTime(slot.end_time)}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AvailableSlotsModal;
