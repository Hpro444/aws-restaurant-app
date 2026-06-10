const MIN_GUESTS = 1;
const MAX_GUESTS = 10;

type GuestsButtonProps = {
  value: number;
  onChange: (guests: number) => void;
};

const GuestsButton = ({ value, onChange }: GuestsButtonProps) => {
  return (
    <div className="flex items-center gap-2 max-w-[255px] justify-between w-full px-6 py-4 bg-white rounded-lg">
      <div className="flex items-center gap-2">
        <span className="pi pi-users text-lg text-[#232323]" />
        <span className="text-gray-800">Guests</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onChange(Math.max(MIN_GUESTS, value - 1))}
          disabled={value <= MIN_GUESTS}
          className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="pi pi-minus" />
        </button>
        <span className="text-gray-800 w-4 text-center">{value}</span>
        <button
          onClick={() => onChange(Math.min(MAX_GUESTS, value + 1))}
          disabled={value >= MAX_GUESTS}
          className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="pi pi-plus" />
        </button>
      </div>
    </div>
  );
};

export default GuestsButton;
