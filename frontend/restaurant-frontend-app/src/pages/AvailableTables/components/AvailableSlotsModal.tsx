import clock_icon from "../../../assets/availableTables/Clock.png";

const formatSlotTime = (iso: string): string => {
  const match = iso.match(/T(\d{2}:\d{2})/);
  return match ? match[1] : iso;
};

const AvailableSlotsModal = () => {
  return (
    <div className="rotate-0 opacity-100 top-[294px] left-[488px] rounded-[24px] p-6 gap-10">
      <div>
        <div>
          <h2>Available slots</h2>
          <button>
            <img src="#" alt="Close" />
          </button>
        </div>
        <p>
          There are 6 slots available at 48 Rustaveli Avenue, Table 1, for
          October 14, 2024
        </p>
      </div>
      <div>
        <div className="grid grid-cols-2 gap-2">
          <button className="font-medium text-[14px] leading-[24px] align-middle border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer hover:bg-green-50">
            <img src={clock_icon} alt="Clock icon" className="w-4 h-4" />
            <span>
              {formatSlotTime("12:00")} - {formatSlotTime("13:00")}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default AvailableSlotsModal;
