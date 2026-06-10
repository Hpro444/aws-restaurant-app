import { useState } from "react";
import { Calendar } from "primereact/calendar";
import {
  isDateOrNull,
  toCalendarTime,
  toTimeString,
} from "../availableTables.services";

type TimeButtonProps = {
  value: string;
  style?: React.CSSProperties;
  onChange: (time: string) => void;
};

const TimeButton = ({ value, style, onChange }: TimeButtonProps) => {
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  return (
    <div className="relative w-full max-w-[200px]" style={style}>
      <div className="border-2 border-[#dadada] rounded-lg h-full flex bg-white px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <Calendar
            value={toCalendarTime(value)}
            onChange={(e) => {
              if (e.value && isDateOrNull(e.value)) {
                onChange(toTimeString(e.value));
              }
            }}
            onShow={() => setIsPanelOpen(true)}
            onHide={() => setIsPanelOpen(false)}
            timeOnly
            hourFormat="24"
            showIcon
            iconPos="left"
            icon="pi pi-clock text-[#232323] text-lg"
            placeholder="Time"
            className="w-full gap-2 items-center"
            inputClassName="w-full text-gray-800 cursor-pointer"
            panelClassName="bg-white text-lg"
            readOnlyInput
          />

          <span
            className={
              "pi pi-chevron-down text-[#232323] text-[14px] transition-transform duration-200 " +
              (isPanelOpen ? "rotate-180" : "")
            }
          />
        </div>
      </div>
    </div>
  );
};

export default TimeButton;
