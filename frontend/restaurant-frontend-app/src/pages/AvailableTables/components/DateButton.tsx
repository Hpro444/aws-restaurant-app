import { Calendar } from "primereact/calendar";
import { useState } from "react";
import {
  isDateOrNull,
  toCalendarDate,
  toLocalApiDate,
} from "../availableTables.services";

type DateButtonProps = {
  value: string;
  onChange: (date: string) => void;
};

const DateButton = ({ value, onChange }: DateButtonProps) => {
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  return (
    <div className="relative w-full max-w-[200px]">
      <div className="border-2 rounded-lg overflow-hidden h-full">
        <div className="w-full cursor-pointer flex items-center justify-between px-6 py-4 bg-white hover:bg-gray-50">
          <Calendar
            value={toCalendarDate(value)}
            onChange={(e) => {
              if (isDateOrNull(e.value) && e.value) {
                onChange(toLocalApiDate(e.value));
              }
            }}
            selectionMode="single"
            onShow={() => setIsPanelOpen(true)}
            onHide={() => setIsPanelOpen(false)}
            showIcon
            iconPos="left"
            icon="pi pi-calendar text-lg text-[#232323]"
            dateFormat="M d, yy"
            placeholder="Date"
            minDate={new Date()}
            className="w-full gap-2 items-center"
            inputClassName="w-full text-gray-800 cursor-pointer"
            panelClassName="bg-white"
            readOnlyInput
          />
          <span
            className={`pi pi-chevron-down text-lg transition-transform text-[#232323] transform pointer-events-none ${isPanelOpen ? "rotate-180" : ""}`}
          />
        </div>
      </div>
    </div>
  );
};

export default DateButton;
