import type { AvailableSlot } from "../../../types/location";
import { formatTime } from "../../../utils/reservationHelpers";

export const SLOTS_PREVIEW = 4;

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
      <span className="pi pi-clock text-lg" />
      <span>
        {formatTime(slot.start_time)} - {formatTime(slot.end_time)}
      </span>
    </button>
  );
};

export default SlotButton;
