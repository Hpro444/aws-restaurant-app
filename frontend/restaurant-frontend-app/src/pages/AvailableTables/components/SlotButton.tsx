import type { AvailableSlot } from "../availableTables.services";
import clock_icon from "../../../assets/availableTables/Clock.png";
import { formatSlotTime } from "../../../utils/reservationHelpers";

const SlotButton = ({
  slot: { start_time, end_time },
}: {
  slot: AvailableSlot;
}) => {
  return (
    <button className="font-medium text-[14px] leading-[24px] align-middle border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer hover:bg-green-50">
      <img src={clock_icon} alt="Clock icon" className="w-4 h-4" />
      <span>
        {formatSlotTime(start_time)} - {formatSlotTime(end_time)}
      </span>
    </button>
  );
};

export default SlotButton;
