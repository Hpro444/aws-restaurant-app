import { type ReservationResponse } from "../reservations.services";
import {
  getStatusColor,
  formatDate,
  formatSlotTime,
} from "../../../utils/reservationHelpers";
import location_icon from "../../../assets/reservations/location-icon.png";
import calendar_icon from "../../../assets/reservations/Calendar.png";
import clock_icon from "../../../assets/reservations/Clock.png";
import people_icon from "../../../assets/reservations/People.png";

interface ReservationCardProps {
  reservation: ReservationResponse;
  onEdit?: (reservation: ReservationResponse) => void;
  onCancel?: (reservationId: string) => void;
  onFeedback?: (reservationId: string) => void;
}

const ReservationCard = ({
  reservation,
  onEdit,
  onCancel,
}: ReservationCardProps) => {
  const {
    reservation_id,
    status,
    location_address,
    date,
    time_from,
    time_to,
    guests_number,
    allowed_actions: { can_edit, can_cancel },
  } = reservation;

  return (
    <div className="flex flex-col gap-12 shadow-[0px_0px_10px_4px_#DADADAB2] p-6 rounded-3xl font-medium text-sm leading-6 tracking-normal align-middle">
      <div className="flex justify-between">
        <div className="flex flex-col gap-2">
          <div className="flex gap-2 items-center">
            <img src={location_icon} alt="Location icon" className="w-3 h-3" />
            <p>{location_address}</p>
          </div>
          <div className="flex gap-2 items-center">
            <img src={calendar_icon} alt="Calendar icon" className="w-3 h-3" />
            <p>{formatDate(date)}</p>
          </div>
          <div className="flex gap-2 items-center">
            <img src={clock_icon} alt="Clock icon" className="w-3 h-3" />
            <p>
              {formatSlotTime(time_from)} - {formatSlotTime(time_to)}
            </p>
          </div>
          <div className="flex gap-2 items-center">
            <img src={people_icon} alt="People icon" className="w-3 h-3" />
            <p>{guests_number} guests</p>
          </div>
        </div>
        <div className="font-light text-xs leading-4 tracking-normal align-middle">
          <p className={`rounded-lg px-3 ${getStatusColor(status)}`}>
            {status}
          </p>
        </div>
      </div>
      <div className="flex justify-end gap-4">
        {can_cancel && (
          <button
            className="border-[#232323] border-b"
            onClick={() => onCancel?.(reservation_id)}
          >
            Cancel
          </button>
        )}
        {can_edit && (
          <button
            className="rounded-lg border border-[#00AD0C] py-2 px-9 bg-white text-[#00AD0C]"
            onClick={() => onEdit?.(reservation)}
          >
            Edit
          </button>
        )}
      </div>
    </div>
  );
};

export default ReservationCard;
