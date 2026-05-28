import type { AvailableSlot } from "../availableTables.services";
import clock_icon from "../../../assets/availableTables/Clock.png";

const formatSlotTime = (iso: string): string => {
  const match = iso.match(/T(\d{2}:\d{2})/);
  return match ? match[1] : iso;
};

const SlotButton = ({ slot }: { slot: AvailableSlot }) => (
  <button className="font-medium text-[14px] leading-[24px] align-middle border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer hover:bg-green-50">
    <img src={clock_icon} alt="Clock icon" className="w-4 h-4" />
    <span>
      {formatSlotTime(slot.start_time)} - {formatSlotTime(slot.end_time)}
    </span>
  </button>
);

export default SlotButton;
