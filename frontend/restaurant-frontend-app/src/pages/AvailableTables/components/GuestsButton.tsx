import people_icon from "../../../assets/availableTables/People.png";
import minus_icon from "../../../assets/availableTables/minus-icon.png";
import plus_icon from "../../../assets/availableTables/plus-icon.png";

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
        <img src={people_icon} alt="Guests icon" />
        <span className="text-gray-800">Guests</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onChange(Math.max(MIN_GUESTS, value - 1))}
          disabled={value <= MIN_GUESTS}
          className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <img src={minus_icon} alt="Minus icon" />
        </button>
        <span className="text-gray-800 w-4 text-center">{value}</span>
        <button
          onClick={() => onChange(Math.min(MAX_GUESTS, value + 1))}
          disabled={value >= MAX_GUESTS}
          className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <img src={plus_icon} alt="Plus icon" />
        </button>
      </div>
    </div>
  );
};

export default GuestsButton;
