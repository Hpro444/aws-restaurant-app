import clock_icon from "../../../assets/availableTables/Clock.png";
import location from "../../../assets/availableTables/location.png";
import location_icon from "../../../assets/availableTables/location-icon.png";
import plus_icon from "../../../assets/availableTables/plus-icon.png";

const CardButton = () => {
  return (
    <button className=" font-medium text-[14px] leading-[24px] align-middle border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer">
      <img src={clock_icon} alt="Clock icon" className="w-4 h-4" />
      <span>12:15 p.m - 1:45 p.m</span>
    </button>
  );
};

const Card = ({ number }: { number: number }) => {
  return (
    <div className="max-w-[664px] flex rounded-3xl shadow-[0px_0px_10px_4px_#DADADAB2] font-medium text-[14px] leading-[24px] tracking-normal align-middle">
      <div>
        <img
          src={location}
          alt="Slika restorana"
          className="w-full h-full object-cover rounded-l-3xl max-w-[200px]"
        />
      </div>
      <div className="flex-1 flex flex-col gap-4 p-6">
        <div className="flex justify-between items-center">
          <p className="flex gap-1 items-center font-medium text-[14px] leading-[24px] tracking-normal align-middle">
            <img src={location_icon} alt="Location icon" className="w-4 h-4" />
            48 Neka lokacija
          </p>
          <p>Table {number}</p>
        </div>
        <p>Table seating capacity: 10 people</p>
        <div className="flex flex-col gap-3">
          <p>6 slots available for Oct 14, 2024:</p>
          <div className="grid grid-cols-2 gap-2">
            <CardButton />
            <CardButton />
            <CardButton />
            <CardButton />
            <button className="font-medium text-[14px] leading-[24px] align-middle justify-self-start border border-[var(--color-brand)] rounded-lg p-2 flex gap-2 items-center cursor-pointer">
              <img src={plus_icon} alt="Plus icon" className="w-4 h-4" />
              <span>Show all</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Card;
