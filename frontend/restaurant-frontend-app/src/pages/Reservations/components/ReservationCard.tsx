import {
  getStatusColor,
  formatDate,
  formatTime,
} from "../../../utils/reservationHelpers";
import type { ReservationResponse } from "../../../types/location";

interface ReservationCardProps {
  reservation: ReservationResponse;
  onEdit?: (reservation: ReservationResponse) => void;
  onCancel?: (reservationId: string) => void;
  onFeedback?: (reservationId: string) => void;
  showCustomerId?: boolean;
}

const ReservationCard = ({
  reservation,
  onEdit,
  onCancel,
  onFeedback,
  showCustomerId = false,
}: ReservationCardProps) => {
  const {
    reservation_id,
    status,
    location_address,
    date,
    time_from,
    time_to,
    guests_number,
    customer_id,
    allowed_actions: { can_edit, can_cancel },
  } = reservation;

  return (
    <div className="min-h-[256px] flex flex-col gap-12 shadow-[0px_0px_10px_4px_#DADADAB2] p-6 rounded-3xl font-medium text-sm leading-6 tracking-normal align-middle h-full">
      <div className="flex justify-between">
        <div className="flex flex-col gap-2">
          <div className="flex gap-2 items-center">
            <span className="pi pi-map-marker text-[var(--color-brand)]" />
            <p>{location_address}</p>
          </div>
          <div className="flex gap-2 items-center">
            <span className="pi pi-calendar text-[var(--color-brand)]" />
            <p>{formatDate(date)}</p>
          </div>
          <div className="flex gap-2 items-center">
            <span className="pi pi-clock text-[var(--color-brand)]" />
            <p>
              {formatTime(time_from)} - {formatTime(time_to)}
            </p>
          </div>
          {showCustomerId ? (
            <div className="flex gap-2 items-center">
              <span className="pi pi-user text-[var(--color-brand)]" />
              <p>Customer {customer_id ?? "-"}</p>
            </div>
          ) : null}
          <div className="flex gap-2 items-center">
            <span className="pi pi-users text-[var(--color-brand)]" />
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
        {onFeedback && status === "In Progress" && (
          <button
            className="cursor-pointer rounded-lg border border-[#00AD0C] py-2 px-9 bg-white text-[#00AD0C]"
            onClick={() => onFeedback?.(reservation_id)}
          >
            Leave Feedback
          </button>
        )}
        {can_cancel && (
          <button
            className="border-[#232323] border-b cursor-pointer"
            onClick={() => onCancel?.(reservation_id)}
          >
            Cancel
          </button>
        )}
        {can_edit && (
          <button
            className="cursor-pointer rounded-lg border border-[#00AD0C] py-2 px-9 bg-white text-[#00AD0C]"
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
