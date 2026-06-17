import locationImg from "../../../assets/home/location.jpg";
import type { Location } from "../../../types/location";

const LocationCard = ({ location }: { location?: Location }) => {
  const locationAddress = location?.address || "Unknown Location";
  const locationImage = location?.image_url || locationImg;
  const totalCapacity = location?.total_capacity || 100;
  const averageOccupancy = location?.average_occupancy || 75;

  return (
    <div className="w-full max-w-[432px] mx-auto">
      <div className="h-[160px] sm:h-[180px] md:h-[140px]">
        <img
          src={locationImage}
          alt={locationAddress}
          className="object-cover h-full w-full rounded-tl-[24px] rounded-tr-[24px]"
          onError={(e) => {
            e.currentTarget.src = locationImg;
          }}
        />
      </div>

      <div className="flex flex-col gap-4 p-4 sm:p-6 rounded-br-[24px] rounded-bl-[24px] shadow-[0px_0px_10px_4px_#DADADAB2]">
        <div className="flex gap-2 items-start">
          <span className="pi pi-map-marker text-[var(--color-brand)] mt-1 shrink-0" />
          <p className="font-medium text-[13px] sm:text-[14px] leading-[22px] sm:leading-[24px] break-words">
            <span>{locationAddress}</span>
          </p>
        </div>

        <div className="flex flex-col sm:flex-row sm:justify-between gap-2 font-poppins font-medium text-[13px] sm:text-[14px] leading-[22px] sm:leading-[24px]">
          <p className="flex flex-col sm:flex-row sm:gap-2">
            <span className="block">Total capacity:</span>
            <span className="block">{totalCapacity} tables</span>
          </p>

          <p className="flex flex-col sm:flex-row sm:gap-2">
            <span className="block">Average occupancy:</span>
            <span className="block">{averageOccupancy}%</span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LocationCard;
