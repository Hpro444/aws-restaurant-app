import { useEffect, useRef, useState } from "react";

type DownloadType = "PDF" | "Excel" | "CSV";

const DownloadButton = ({ className }: { className?: string }) => {
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const handleSelect = (type: DownloadType) => {
    setIsOpen(false);

    console.log("Selected download type:", type);
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
    <div ref={wrapperRef} className={`relative inline-block w-[220px] ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="cursor-pointer w-full px-3 py-2 border border-[#00ad0c] rounded-lg text-[#00ad0c] flex items-center justify-between"
      >
        <span className="font-bold">Download</span>

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

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-full bg-white border rounded-lg shadow-md z-20">
          <button
            type="button"
            onClick={() => handleSelect("PDF")}
            className="cursor-pointer w-full text-left px-3 py-2 hover:bg-green-50 rounded-t-lg"
          >
            Download in PDF
          </button>
          <button
            type="button"
            onClick={() => handleSelect("Excel")}
            className="cursor-pointer w-full text-left px-3 py-2 hover:bg-green-50"
          >
            Download in Excel
          </button>
          <button
            type="button"
            onClick={() => handleSelect("CSV")}
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
