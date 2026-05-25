import location from "../../../assets/home/location.jpg";
import location_icon from "../../../assets/home/location-icon.png";

const LocationCard = () => {
  return (
    <div className="max-h-[256px] w-[432px]">
      <div className="h-[140px]">
        <img
          src={location}
          alt="Image"
          className="rotate-0 object-cover h-full opacity-100 w-full rounded-tl-[24px] rounded-tr-[24px]"
        />
      </div>
      <div className="flex gap-5 flex-col rotate-0 opacity-100 p-6 rounded-br-[24px] rounded-bl-[24px] shadow-[0px_0px_10px_4px_#DADADAB2]">
        <div className="flex gap-2 items-center">
          <img src={location_icon} alt="Location" />
          <p className="font-medium text-[14px] leading-[24px] align-middle">
            <span>48 Text</span>
          </p>
        </div>
        <div className="flex justify-between font-poppins font-medium text-[14px] leading-[24px] align-middle">
          <p className="flex gap-2">
            <span>Total capacity:</span> <span>100 tables</span>
          </p>
          <p className="flex gap-2">
            <span>Average occupancy:</span> <span>75%</span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LocationCard;
