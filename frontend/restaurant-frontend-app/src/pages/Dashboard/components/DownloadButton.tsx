import { useEffect, useRef, useState } from "react";
import type { ReportFileFormat } from "../dashboard.services";

interface DownloadButtonProps {
  className?: string;
  onSelectFormat: (type: ReportFileFormat) => Promise<void> | void;
  disabled?: boolean;
  isLoading?: boolean;
}

const DownloadButton = ({
  className,
  onSelectFormat,
  disabled = false,
  isLoading = false,
}: DownloadButtonProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const handleSelect = async (type: ReportFileFormat) => {
    setIsOpen(false);
    await onSelectFormat(type);
  };

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div
      ref={wrapperRef}
      className={`relative inline-block w-[220px] ${className || ""}`}
    >
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        disabled={disabled || isLoading}
        className={
          "w-full px-3 py-2 border border-[#00ad0c] rounded-lg text-[#00ad0c] flex items-center justify-between " +
          (disabled || isLoading
            ? "opacity-60 cursor-not-allowed"
            : "cursor-pointer")
        }
      >
        <span className="font-bold">
          {isLoading ? "Downloading..." : "Download"}
        </span>

        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
          viewBox="0 0 20 20"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M5 7.5L10 12.5L15 7.5"
            stroke="#00ad0c"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {isOpen && !disabled && !isLoading && (
        <div className="absolute top-full left-0 mt-2 w-full bg-white border rounded-lg shadow-md z-20">
          <button
            type="button"
            onClick={() => handleSelect("pdf")}
            className="cursor-pointer w-full text-left px-3 py-2 hover:bg-green-50 rounded-t-lg"
          >
            Download in PDF
          </button>
          <button
            type="button"
            onClick={() => handleSelect("excel")}
            className="cursor-pointer w-full text-left px-3 py-2 hover:bg-green-50"
          >
            Download in Excel
          </button>
          <button
            type="button"
            onClick={() => handleSelect("csv")}
            className="cursor-pointer w-full text-left px-3 py-2 hover:bg-green-50 rounded-b-lg"
          >
            Download in CSV
          </button>
        </div>
      )}
    </div>
  );
};

export default DownloadButton;
